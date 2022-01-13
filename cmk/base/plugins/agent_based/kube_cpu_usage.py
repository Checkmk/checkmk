#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from typing import Literal, Optional

from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, register, Result, Service, State
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import (
    CheckResult,
    DiscoveryResult,
    StringTable,
)
from cmk.base.plugins.agent_based.utils.kube_resources import (
    AggregatedLimit,
    check_with_utilization,
    DEFAULT_PARAMS,
    ExceptionalResource,
    iterate_resources,
    Params,
    Resources,
    result_for_exceptional_resource,
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


def check_resource(
    params: Params,
    requirement_type: Literal["request", "limit"],
    requirement_value: AggregatedLimit,
    cpu_usage: float,
) -> CheckResult:
    if isinstance(requirement_value, ExceptionalResource):
        yield result_for_exceptional_resource(requirement_type, requirement_value)
        return
    if requirement_value == 0:
        yield Result(
            state=State.OK,
            summary=f"{requirement_type.title()} n/a",
            details=f"{requirement_type.title()}: set to zero for all containers",
        )
        return
    yield from check_with_utilization(
        cpu_usage,
        "cpu",
        requirement_type,
        requirement_value,
        params[requirement_type],
        lambda x: f"{x:0.3f}",
    )


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
    for requirement_type, requirement_value in iterate_resources(section_kube_cpu_resources):
        yield from check_resource(params, requirement_type, requirement_value, cpu_usage)


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
    check_default_parameters=DEFAULT_PARAMS,
)
