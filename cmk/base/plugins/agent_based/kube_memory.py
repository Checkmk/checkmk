#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import json
from typing import Optional

from cmk.base.plugins.agent_based.utils.k8s import Memory
from cmk.base.plugins.agent_based.utils.kube_resources import (
    check_with_utilization,
    DEFAULT_PARAMS,
    iterate_resources,
    Params,
    Resources,
    result_for_exceptional_resource,
)

from .agent_based_api.v1 import Metric, register, render, Result, Service, State
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable


def parse_memory_resources(string_table: StringTable) -> Resources:
    """
    >>> parse_memory_resources([['{"request": 23120704.0, "limit": 28120704.0}']])
    Resources(request=23120704.0, limit=28120704.0)
    >>> parse_memory_resources([['{"request": "unspecified", "limit": "unspecified"}']])
    Resources(request=<ExceptionalResource.unspecified: 'unspecified'>, limit=<ExceptionalResource.unspecified: 'unspecified'>)
    >>> parse_memory_resources([['{"request": 0.0, "limit": "zero"}']])
    Resources(request=0.0, limit=<ExceptionalResource.zero: 'zero'>)
    """
    return Resources(**json.loads(string_table[0][0]))


def parse_performance_memory(string_table: StringTable) -> Memory:
    """
    >>> parse_performance_memory([['{"memory_usage_bytes": 18120704.0}']])
    Memory(memory_usage_bytes=18120704.0)
    """
    return Memory(**json.loads(string_table[0][0]))


register.agent_section(
    name="kube_memory_resources_v1",
    parse_function=parse_memory_resources,
    parsed_section_name="kube_memory_resources",
)


register.agent_section(
    name="k8s_live_memory_v1",
    parse_function=parse_performance_memory,
    parsed_section_name="k8s_live_memory",
)


# TODO Add different logic, service should always be discovered, but instead be pending
# (not unknown)
def discovery_kube_memory(
    section_kube_memory_resources, section_k8s_live_memory
) -> DiscoveryResult:
    if section_k8s_live_memory is not None and section_kube_memory_resources is not None:
        yield Service()


# TODO This should be moved to utils, and used jointly by kube_container_memory and kube_container_cpu
# TODO Add Perf-O-Meter
def check_kube_memory(
    params: Params,
    section_kube_memory_resources: Optional[Resources],
    section_k8s_live_memory: Optional[Memory],
) -> CheckResult:
    if section_k8s_live_memory is None or section_kube_memory_resources is None:
        return

    total_usage = section_k8s_live_memory.memory_usage_bytes
    yield Result(state=State.OK, summary=f"Usage: {render.bytes(total_usage)}")
    yield Metric("kube_memory_usage", total_usage)

    for requirement_name, requirement in iterate_resources(section_kube_memory_resources):
        if requirement == 0:
            yield Result(
                state=State.OK,
                summary=f"{requirement_name.title()}: n/a",
                details=f"{requirement_name.title()}: set to zero for all containers",
            )
        elif isinstance(requirement, float):
            param = params[requirement_name]
            yield from check_with_utilization(
                total_usage,
                "memory",
                requirement_name,
                requirement,
                param,
                render.bytes,
            )
        else:
            yield result_for_exceptional_resource(requirement_name, requirement)


register.check_plugin(
    name="kube_memory",  # TODO change this plugin name
    service_name="Container memory",  # TODO change this service name
    sections=["kube_memory_resources", "k8s_live_memory"],
    discovery_function=discovery_kube_memory,
    check_function=check_kube_memory,
    check_ruleset_name="kube_memory",
    check_default_parameters=DEFAULT_PARAMS,
)
