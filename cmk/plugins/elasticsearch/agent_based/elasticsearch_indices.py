#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import dataclasses
import json
import re
import time
from collections.abc import Callable, Iterable, Mapping, MutableMapping, Sequence
from typing import Any, NotRequired, TypedDict

import pydantic

from cmk.agent_based.v1 import check_levels as check_levels_v1
from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_average,
    get_rate,
    get_value_store,
    GetRateError,
    render,
    Service,
    StringTable,
)


class _DocsResponse(pydantic.BaseModel, frozen=True):
    count: int


class _PrimariesResponse(pydantic.BaseModel, frozen=True):
    docs: _DocsResponse


class _StoreReponse(pydantic.BaseModel, frozen=True):
    size_in_bytes: int


class _TotalResponse(pydantic.BaseModel, frozen=True):
    store: _StoreReponse


class _IndexResponse(pydantic.BaseModel, frozen=True):
    primaries: _PrimariesResponse
    total: _TotalResponse


@dataclasses.dataclass(frozen=True)
class _ElasticIndex:
    count: float
    size: float


_Section = Mapping[str, _ElasticIndex]


def parse_elasticsearch_indices(string_table: StringTable) -> _Section:
    return {
        index_name: _ElasticIndex(
            count=index_response.primaries.docs.count,
            size=index_response.total.store.size_in_bytes,
        )
        for index_name, index_response in (
            (index_name, _IndexResponse.model_validate(raw_dict))
            for index_name, raw_dict in json.loads(string_table[0][0]).items()
        )
    }


agent_section_elasticsearch_indices = AgentSection(
    name="elasticsearch_indices",
    parse_function=parse_elasticsearch_indices,
)


class _DiscoveryParams(TypedDict):
    grouping: tuple[str, Iterable[str]]


def discover_elasticsearch_indices(params: _DiscoveryParams, section: _Section) -> DiscoveryResult:
    groups: dict[str, str] = {}
    grouped_indices: set[str] = set()

    for pattern in params["grouping"][1]:
        compiled_pattern = re.compile(pattern)
        for index_name in section:
            if match := compiled_pattern.search(index_name):
                groups.setdefault(match.group(), pattern)
                grouped_indices.add(index_name)

    yield from (
        Service(item=group_name, parameters={"grouping_regex": group_pattern})
        for group_name, group_pattern in groups.items()
    )
    yield from (
        Service(item=index_name, parameters={"grouping_regex": None})
        for index_name in set(section) - grouped_indices
    )


class _CheckParams(TypedDict):
    grouping_regex: str | None
    elasticsearch_count_rate: NotRequired[tuple[float, float, int]]
    elasticsearch_size_rate: NotRequired[tuple[float, float, int]]


def check_elasticsearch_indices(
    item: str,
    params: _CheckParams,
    section: _Section,
) -> CheckResult:
    yield from _check_elasticsearch_indices(
        item=item,
        params=params,
        section=section,
        value_store=get_value_store(),
        now=time.time(),
    )


def _check_elasticsearch_indices(
    *,
    item: str,
    params: _CheckParams,
    section: _Section,
    value_store: MutableMapping[str, Any],
    now: float,
) -> CheckResult:
    if not (
        accumulated_index := _accumulate_indices(
            item,
            params["grouping_regex"],
            section,
        )
    ):
        return
    yield from _check_index(
        index=accumulated_index,
        params=params,
        value_store=value_store,
        now=now,
    )


def _accumulate_indices(
    item: str,
    grouping_regex: str | None,
    section: _Section,
) -> _ElasticIndex | None:
    if grouping_regex is None:
        return section.get(item)
    compiled_pattern = re.compile(grouping_regex)
    return _do_accumulation(
        [
            index
            for index_name, index in section.items()
            if (match := compiled_pattern.search(index_name)) and match.group() == item
        ]
    )


def _do_accumulation(group_members: Sequence[_ElasticIndex]) -> _ElasticIndex | None:
    return (
        _ElasticIndex(
            count=sum(index.count for index in group_members),
            size=sum(index.size for index in group_members),
        )
        if group_members
        else None
    )


def _check_index(
    *,
    index: _ElasticIndex,
    params: _CheckParams,
    value_store: MutableMapping[str, Any],
    now: float,
) -> CheckResult:
    for metric_value, metric_name, metric_params, label, render_func in [
        (
            index.count,
            "elasticsearch_count",
            params.get("elasticsearch_count_rate", (None, None, 30)),
            "Document count",
            lambda v: str(round(v)),
        ),
        (
            index.size,
            "elasticsearch_size",
            params.get("elasticsearch_size_rate", (None, None, 30)),
            "Size",
            render.bytes,
        ),
    ]:
        yield from _check_metric(
            metric_value=metric_value,
            metric_name=metric_name,
            metric_params=metric_params,
            label=label,
            render_func=render_func,
            value_store=value_store,
            now=now,
        )


def _check_metric(
    *,
    metric_value: float,
    metric_name: str,
    metric_params: tuple[float, float, int] | tuple[None, None, int],
    label: str,
    render_func: Callable[[float], str],
    value_store: MutableMapping[str, Any],
    now: float,
) -> CheckResult:
    yield from check_levels_v1(
        metric_value,
        metric_name=metric_name,
        render_func=render_func,
        label=label,
    )

    try:
        rate = (
            get_rate(
                value_store=value_store,
                key=metric_name,
                time=now,
                value=metric_value,
            )
            * 60
        )
    except GetRateError:
        return

    # always compute the average st. we have a backlog available in case we need it
    rate_warn, rate_crit, avg_horizon = metric_params
    avg_rate = get_average(
        value_store=value_store,
        key=f"{metric_name}.average",
        time=now,
        value=rate,
        backlog_minutes=avg_horizon,
    )

    levels_rate = None
    if rate_warn is not None and rate_crit is not None:
        levels_rate = (
            avg_rate * (rate_warn / 100.0 + 1),
            avg_rate * (rate_crit / 100.0 + 1),
        )

    yield from check_levels_v1(
        rate,
        levels_upper=levels_rate,
        metric_name=f"{metric_name}_rate",
        render_func=lambda v: f"{render_func(v)}/minute",
        label=f"{label} rate",
    )


check_plugin_elasticsearch_indices = CheckPlugin(
    name="elasticsearch_indices",
    service_name="Elasticsearch Indice %s",
    discovery_function=discover_elasticsearch_indices,
    discovery_ruleset_name="elasticsearch_indices_disovery",
    discovery_default_parameters={"grouping": ("disabled", [])},
    check_function=check_elasticsearch_indices,
    check_ruleset_name="elasticsearch_indices",
    check_default_parameters={"grouping_regex": None},
)
