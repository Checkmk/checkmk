#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import time
from collections.abc import MutableMapping
from typing import Any

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_value_store,
    Service,
)
from cmk.plugins.kube.schemata.section import AllocatableResource, PerformanceUsage, Resources
from cmk.plugins.lib.kube_resources import (
    check_resource,
    cpu_render_func,
    DEFAULT_PARAMS,
    Params,
    parse_allocatable_resource,
    parse_performance_usage,
    parse_resources,
    performance_cpu,
)


def discovery_kube_cpu(
    section_kube_performance_cpu: PerformanceUsage | None,
    section_kube_cpu_resources: Resources | None,
    section_kube_allocatable_cpu_resource: AllocatableResource | None,
) -> DiscoveryResult:
    yield Service()


def check_kube_cpu(
    params: Params,
    section_kube_performance_cpu: PerformanceUsage | None,
    section_kube_cpu_resources: Resources | None,
    section_kube_allocatable_cpu_resource: AllocatableResource | None,
) -> CheckResult:
    yield from _check_kube_cpu(
        params,
        section_kube_performance_cpu,
        section_kube_cpu_resources,
        section_kube_allocatable_cpu_resource,
        current_timestamp=time.time(),
        host_value_store=get_value_store(),
    )


def _check_kube_cpu(
    params: Params,
    section_kube_performance_cpu: PerformanceUsage | None,
    section_kube_cpu_resources: Resources | None,
    section_kube_allocatable_cpu_resource: AllocatableResource | None,
    current_timestamp: float,
    host_value_store: MutableMapping[str, Any],
) -> CheckResult:
    assert section_kube_cpu_resources is not None
    yield from check_resource(
        params,
        performance_cpu(
            section_kube_performance_cpu,
            current_timestamp,
            host_value_store,
            value_store_key="cpu_usage",
        ),
        section_kube_cpu_resources,
        section_kube_allocatable_cpu_resource,
        "cpu",
        cpu_render_func,
    )


agent_section_kube_performance_cpu_v1 = AgentSection(
    name="kube_performance_cpu_v1",
    parsed_section_name="kube_performance_cpu",
    parse_function=parse_performance_usage,
)


agent_section_kube_cpu_resources_v1 = AgentSection(
    name="kube_cpu_resources_v1",
    parsed_section_name="kube_cpu_resources",
    parse_function=parse_resources,
)

agent_section_kube_allocatable_cpu_resource_v1 = AgentSection(
    name="kube_allocatable_cpu_resource_v1",
    parsed_section_name="kube_allocatable_cpu_resource",
    parse_function=parse_allocatable_resource,
)

check_plugin_kube_cpu = CheckPlugin(
    name="kube_cpu",
    service_name="CPU resources",
    sections=["kube_performance_cpu", "kube_cpu_resources", "kube_allocatable_cpu_resource"],
    check_ruleset_name="kube_cpu",
    discovery_function=discovery_kube_cpu,
    check_function=check_kube_cpu,
    check_default_parameters=DEFAULT_PARAMS,
)
