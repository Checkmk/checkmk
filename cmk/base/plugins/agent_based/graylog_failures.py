#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from typing import Any, Iterable, Mapping, Sequence

from pydantic import BaseModel

from .agent_based_api.v1 import check_levels, register, render, Result, Service, State
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable
from .utils.graylog import deserialize_and_merge_json


class FailureMessage(BaseModel):
    type: str | None
    reason: str | None

    def to_human_readable(self) -> Iterable[str]:
        yield from (
            f"{field_name.title()}: {field_value}"
            for field_name, field_value in self.dict(exclude_none=True).items()
        )


class Failure(BaseModel):
    timestamp: str | None
    index: str | None
    message: FailureMessage | str | None

    @classmethod
    def from_partially_raw(cls, raw: Mapping[str, Any]) -> "Failure":
        return cls(
            timestamp=raw.get("timestamp"),
            index=raw.get("index"),
            # message can either be a json-encoded dict or a non-json string
            message=cls._parse_message(raw_msg)
            if (raw_msg := raw.get("message")) is not None
            else None,
        )

    @staticmethod
    def _parse_message(raw: str) -> str | FailureMessage:
        try:
            deserialized = json.loads(raw)
        except json.JSONDecodeError:
            # the graylog API does not specify the scheme of the endpoint providing this data (it only
            # says 'anyMap'), see SUP-11170
            return raw
        return FailureMessage.parse_obj(deserialized)

    def to_human_readable(self) -> Iterable[str]:
        for field_name, field_value in dict(self).items():
            match field_value:
                case str():
                    yield f"{field_name.title()}: {field_value}"
                case FailureMessage():
                    yield from field_value.to_human_readable()


class Section(BaseModel):
    failures: Sequence[Failure]
    total: int | None
    count: int | None
    ds_param_since: float

    @classmethod
    def from_partially_raw(cls, raw: dict[str, Any]) -> "Section | None":
        # The data model we have to deal with here is not a proper json model: the error message of
        # a failure can either be a json-encoded dict (so json inside json) or a non-json string,
        # which is why neither parse_obj nor parse_raw can do the job
        return (
            None
            if (raw_failures := raw.get("failures")) is None
            else cls(
                failures=[Failure.from_partially_raw(raw_failure) for raw_failure in raw_failures],
                total=raw.get("total"),
                count=raw.get("count"),
                ds_param_since=raw["ds_param_since"],
            )
        )


def parse(string_table: StringTable) -> Section | None:
    return Section.from_partially_raw(deserialize_and_merge_json(string_table))


register.agent_section(
    name="graylog_failures",
    parse_function=parse,
)


def discover(section: Section) -> DiscoveryResult:
    yield Service()


def _failure_results(failures: Iterable[Failure]) -> CheckResult:
    indices_affected = set()
    details = []

    for failure in sorted(
        failures,
        key=lambda f: (f.timestamp, f.index),
    ):
        if failure.index is not None:
            indices_affected.add(failure.index)
        if failure_human_readable := ", ".join(failure.to_human_readable()):
            details.append(failure_human_readable)

    if details:
        yield Result(
            state=State.OK,
            summary=f"Affected indices: {len(indices_affected)}, see service details for further information",
        )
        yield Result(
            state=State.OK,
            notice="\n".join(details),
        )


def check(
    params: Mapping[str, Any],
    section: Section,
) -> CheckResult:
    if section.total is not None:
        yield from check_levels(
            value=section.total,
            levels_upper=params.get("failures"),
            metric_name="failures",
            render_func=str,
            label="Total number of failures",
        )

    if section.count is None:
        return

    yield from check_levels(
        value=section.count,
        levels_upper=params.get("failures_last"),
        metric_name=None,
        render_func=str,
        label="Failures in last %s" % render.timespan(section.ds_param_since),
    )

    if not section.count:
        return

    yield from _failure_results(section.failures)


register.check_plugin(
    name="graylog_failures",
    service_name="Graylog Index Failures",
    discovery_function=discover,
    check_function=check,
    check_default_parameters={},
    check_ruleset_name="graylog_failures",
)
