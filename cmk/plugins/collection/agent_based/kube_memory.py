#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    render,
    Service,
)
from cmk.plugins.kube.schemata.section import AllocatableResource, PerformanceUsage, Resources
from cmk.plugins.lib.kube_resources import (
    check_resource,
    DEFAULT_PARAMS,
    Params,
    parse_allocatable_resource,
    parse_performance_usage,
    parse_resources,
)

agent_section_kube_memory_resources_v1 = AgentSection(
    name="kube_memory_resources_v1",
    parse_function=parse_resources,
    parsed_section_name="kube_memory_resources",
)


agent_section_kube_performance_memory_v1 = AgentSection(
    name="kube_performance_memory_v1",
    parse_function=parse_performance_usage,
    parsed_section_name="kube_performance_memory",
)


agent_section_kube_allocatable_memory_resource_v1 = AgentSection(
    name="kube_allocatable_memory_resource_v1",
    parsed_section_name="kube_allocatable_memory_resource",
    parse_function=parse_allocatable_resource,
)


def discovery_kube_memory(
    section_kube_performance_memory: PerformanceUsage | None,
    section_kube_memory_resources: Resources | None,
    section_kube_allocatable_memory_resource: AllocatableResource | None,
) -> DiscoveryResult:
    yield Service()


def check_kube_memory(
    params: Params,
    section_kube_performance_memory: PerformanceUsage | None,
    section_kube_memory_resources: Resources | None,
    section_kube_allocatable_memory_resource: AllocatableResource | None,
) -> CheckResult:
    assert section_kube_memory_resources is not None
    yield from check_resource(
        params,
        section_kube_performance_memory,
        section_kube_memory_resources,
        section_kube_allocatable_memory_resource,
        "memory",
        render.bytes,
    )


check_plugin_kube_memory = CheckPlugin(
    name="kube_memory",
    service_name="Memory resources",
    sections=[
        "kube_performance_memory",
        "kube_memory_resources",
        "kube_allocatable_memory_resource",
    ],
    discovery_function=discovery_kube_memory,
    check_function=check_kube_memory,
    check_ruleset_name="kube_memory",
    check_default_parameters=DEFAULT_PARAMS,
)
