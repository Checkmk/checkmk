#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from typing import Literal, Optional, Tuple, TypedDict, Union

from cmk.base.plugins.agent_based.agent_based_api.v1 import (
    check_levels,
    Metric,
    register,
    render,
    Result,
    Service,
    State,
)
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import (
    CheckResult,
    DiscoveryResult,
    StringTable,
)
from cmk.base.plugins.agent_based.utils.kube import (
    AggregatedLimit,
    AggregatedRequest,
    ExceptionalResource,
    Resources,
    Usage,
)


def parse_kube_live_cpu_usage_v1(string_table: StringTable) -> Usage:
    """Parses usage value into Usage"""
    return Usage(**json.loads(string_table[0][0]))


def parse_kube_cpu_resources_v1(string_table: StringTable) -> Resources:
    """Parses limit and request values into Resources"""
    return Resources(**json.loads(string_table[0][0]))


def discovery(
    section_kube_live_cpu_usage: Optional[Usage],
    section_kube_cpu_resources: Optional[Resources],
) -> DiscoveryResult:
    if section_kube_live_cpu_usage is not None:
        yield Service()


Modes = Literal["perc_used"]
Param = Union[Literal["ignore"], Tuple[Modes, Tuple[float, float]]]


class Params(TypedDict):
    request: Param
    limit: Param


def get_levels_for(params: Params, key: str) -> Optional[Tuple[float, float]]:
    """Get the levels for the given key from the params

    Examples:
        >>> params = Params(
        ...     request="ignore",
        ...     limit=("perc_used", (80.0, 90.0)),
        ... )
        >>> get_levels_for(params, "request")
        >>> get_levels_for(params, "limit")
        (80.0, 90.0)
    """
    levels = params.get(key, "ignore")
    if levels == "ignore":
        return None
    assert isinstance(levels, tuple)
    return levels[1]


def check_resource(
    params: Params,
    resource_type: str,
    resource_value: Union[AggregatedLimit, AggregatedRequest],
    cpu_usage: float,
) -> CheckResult:
    if isinstance(resource_value, ExceptionalResource):
        yield Result(
            state=State.OK,
            summary=f"{resource_type.title()} n/a",
            details=f"{resource_type.title()}: {resource_value}",
        )
        return
    if resource_value == 0:
        yield Result(
            state=State.OK,
            summary=f"{resource_type.title()} n/a",
            details=f"{resource_type.title()}: set to zero for all containers",
        )
        return
    yield Metric(f"kube_cpu_{resource_type}", resource_value)
    utilization = cpu_usage / resource_value * 100
    result, metric = check_levels(
        utilization,
        levels_upper=get_levels_for(params, resource_type),
        metric_name=f"kube_cpu_{resource_type}_utilization",
        render_func=render.percent,
    )
    assert isinstance(result, Result)
    percentage, *warn_crit = result.summary.split()
    yield Result(
        state=result.state,
        summary=f"{resource_type.title()} utilization: {percentage} - {cpu_usage:0.3f} of {resource_value:0.3f} {' '.join(warn_crit)}".rstrip(),
    )
    yield metric


def check(
    params: Params,
    section_kube_live_cpu_usage: Optional[Usage],
    section_kube_cpu_resources: Optional[Resources],
) -> CheckResult:
    if section_kube_live_cpu_usage is None:
        return
    cpu_usage = section_kube_live_cpu_usage.usage
    yield Result(state=State.OK, summary=f"Usage: {cpu_usage:0.3f}")
    yield Metric("kube_cpu_usage", cpu_usage)
    if section_kube_cpu_resources is None:
        return
    yield from check_resource(params, "request", section_kube_cpu_resources.request, cpu_usage)
    yield from check_resource(params, "limit", section_kube_cpu_resources.limit, cpu_usage)


register.agent_section(
    name="k8s_live_cpu_usage_v1",
    parsed_section_name="kube_live_cpu_usage",
    parse_function=parse_kube_live_cpu_usage_v1,
)

register.agent_section(
    name="kube_cpu_resources_v1",
    parsed_section_name="kube_cpu_resources",
    parse_function=parse_kube_cpu_resources_v1,
)

register.check_plugin(
    name="kube_cpu_usage",
    service_name="CPU",  # FIXME: YTBD
    sections=["kube_live_cpu_usage", "kube_cpu_resources"],
    check_ruleset_name="kube_cpu_usage",
    discovery_function=discovery,
    check_function=check,
    check_default_parameters={},
)
