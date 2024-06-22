#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
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
from cmk.plugins.kube.schemata.section import HardResourceRequirement, PerformanceUsage
from cmk.plugins.lib.kube_resources import (
    check_resource_quota_resource,
    cpu_render_func,
    Params,
    parse_hard_requirements,
    parse_performance_usage,
    performance_cpu,
    RESOURCE_QUOTA_DEFAULT_PARAMS,
)

agent_section_kube_resource_quota_cpu_resources_v1 = AgentSection(
    name="kube_resource_quota_cpu_resources_v1",
    parse_function=parse_hard_requirements,
    parsed_section_name="kube_resource_quota_cpu_resources",
)


agent_section_kube_resource_quota_performance_cpu_v1 = AgentSection(
    name="kube_resource_quota_performance_cpu_v1",
    parse_function=parse_performance_usage,
    parsed_section_name="kube_resource_quota_performance_cpu",
)


def discovery_kube_resource_quota_cpu(
    section_kube_resource_quota_performance_cpu: PerformanceUsage | None,
    section_kube_resource_quota_cpu_resources: HardResourceRequirement | None,
) -> DiscoveryResult:
    yield Service()


def check_kube_resource_quota_cpu(
    params: Params,
    section_kube_resource_quota_performance_cpu: PerformanceUsage | None,
    section_kube_resource_quota_cpu_resources: HardResourceRequirement | None,
) -> CheckResult:
    yield from _check_kube_resource_quota_cpu(
        params,
        section_kube_resource_quota_performance_cpu,
        section_kube_resource_quota_cpu_resources,
        current_timestamp=time.time(),
        host_value_store=get_value_store(),
    )


def _check_kube_resource_quota_cpu(
    params: Params,
    section_kube_resource_quota_performance_cpu: PerformanceUsage | None,
    section_kube_resource_quota_cpu_resources: HardResourceRequirement | None,
    current_timestamp: float,
    host_value_store: MutableMapping[str, Any],
) -> CheckResult:
    yield from check_resource_quota_resource(
        params=params,
        resource_usage=performance_cpu(
            section_kube_resource_quota_performance_cpu,
            current_timestamp,
            host_value_store,
            value_store_key="resource_quota_cpu_usage",
        ),
        hard_requirement=section_kube_resource_quota_cpu_resources,
        resource_type="cpu",
        render_func=cpu_render_func,
    )


check_plugin_kube_resource_quota_cpu = CheckPlugin(
    name="kube_resource_quota_cpu",
    service_name="Resource quota cpu resources",
    sections=[
        "kube_resource_quota_performance_cpu",
        "kube_resource_quota_cpu_resources",
    ],
    discovery_function=discovery_kube_resource_quota_cpu,
    check_function=check_kube_resource_quota_cpu,
    check_ruleset_name="kube_resource_quota_cpu",
    check_default_parameters=RESOURCE_QUOTA_DEFAULT_PARAMS,
)
