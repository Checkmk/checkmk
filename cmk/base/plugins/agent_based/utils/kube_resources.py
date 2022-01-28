#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from typing import Callable, Iterable, Literal, Optional, Sequence, Tuple, TypedDict, Union

from pydantic import BaseModel

from cmk.base.plugins.agent_based.agent_based_api.v1 import check_levels, Metric, render, Result
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import CheckResult, StringTable


class Resources(BaseModel):
    """sections: "[kube_memory_resources_v1, kube_cpu_resources_v1]"""

    request: float
    limit: float
    count_unspecified_requests: int
    count_unspecified_limits: int
    count_zeroed_limits: int
    count_total: int


def iterate_resources(
    resources: Resources,
) -> Sequence[Tuple[Literal["request", "limit"], float]]:
    return [("request", resources.request), ("limit", resources.limit)]


def count_overview(resources: Resources, requirement: Literal["request", "limit"]) -> str:
    ignored = (
        resources.count_unspecified_requests
        if requirement == "request"
        else resources.count_unspecified_limits + resources.count_zeroed_limits
    )
    return (
        f"{resources.count_total - ignored}/{resources.count_total} containers with {requirement}s"
    )


def parse_resources(string_table: StringTable) -> Resources:
    """Parses limit and request values into Resources
    >>> parse_resources([['{"request": 209715200.0,'
    ... '"limit": 104857600.0,'
    ... '"count_unspecified_requests": 0,'
    ... '"count_unspecified_limits": 0,'
    ... '"count_zeroed_limits": 1,'
    ... '"count_total": 1}']])
    Resources(request=209715200.0, limit=104857600.0, count_unspecified_requests=0, count_unspecified_limits=0, count_zeroed_limits=1, count_total=1)
    """
    return Resources(**json.loads(string_table[0][0]))


class Usage(BaseModel):
    usage: float


Param = Union[Literal["no_levels"], Tuple[Literal["levels"], Tuple[float, float]]]


class Params(TypedDict):
    usage: Param
    request: Param
    limit: Param


DEFAULT_PARAMS = Params(
    usage="no_levels",
    request="no_levels",
    limit="no_levels",
)


def check_with_utilization(
    usage: float,
    resource_type: Literal["memory", "cpu"],
    requirement_type: Literal["limit", "request"],
    requirement_value: float,
    param: Param,
    render_func: Callable[[float], str],
) -> Iterable[Union[Metric, Result]]:
    utilization = usage * 100.0 / requirement_value
    result, metric = check_levels(
        utilization,
        levels_upper=param[1] if param != "no_levels" else None,
        metric_name=f"kube_{resource_type}_{requirement_type}_utilization",
        render_func=render.percent,
        boundaries=(0.0, None),
    )
    assert isinstance(result, Result)
    percentage, *warn_crit = result.summary.split()
    yield Result(
        state=result.state,
        summary=" ".join(
            [
                f"{requirement_type.title()} utilization: {percentage} - {render_func(usage)} of {render_func(requirement_value)}"
            ]
            + warn_crit
        ),
    )
    yield metric


def check_resource(
    params: Params,
    usage: Optional[Usage],
    resources: Resources,
    resource_type: Literal["memory", "cpu"],
    render_func: Callable[[float], str],
) -> CheckResult:
    if usage is not None:
        total_usage = usage.usage
        yield from check_levels(
            total_usage,
            label="Usage",
            levels_upper=params["usage"][1] if params["usage"] != "no_levels" else None,
            metric_name=f"kube_{resource_type}_usage",
            render_func=render_func,
            boundaries=(0.0, None),
        )

    for requirement_name, requirement in iterate_resources(resources):
        if requirement != 0.0 and usage is not None:
            result, metric = check_with_utilization(
                total_usage,
                resource_type,
                requirement_name,
                requirement,
                params[requirement_name],
                render_func,
            )
            yield Metric(f"kube_{resource_type}_{requirement_name}", requirement)
        else:  # requirements with no usage
            result, metric = check_levels(
                requirement,
                label=requirement_name.title(),
                metric_name=f"kube_{resource_type}_{requirement_name}",
                render_func=render_func,
                boundaries=(0.0, None),
            )
        assert isinstance(result, Result)
        yield Result(
            state=result.state,
            summary=f"{result.summary} ({count_overview(resources, requirement_name)})",
        )
        yield metric
