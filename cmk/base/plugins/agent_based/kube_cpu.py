#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import time
from typing import Any, MutableMapping, Optional

from cmk.base.plugins.agent_based.agent_based_api.v1 import get_value_store, register, Service
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import CheckResult, DiscoveryResult
from cmk.base.plugins.agent_based.utils.kube import PerformanceUsage
from cmk.base.plugins.agent_based.utils.kube_resources import (
    AllocatableResource,
    check_resource,
    CPU_RENDER_FUNC,
    DEFAULT_PARAMS,
    Params,
    parse_allocatable_resource,
    parse_performance_usage,
    parse_resources,
    performance_cpu,
    Resources,
)


def discovery_kube_cpu(
    section_kube_performance_cpu: Optional[PerformanceUsage],
    section_kube_cpu_resources: Optional[Resources],
    section_kube_allocatable_cpu_resource: Optional[AllocatableResource],
) -> DiscoveryResult:
    yield Service()


def check_kube_cpu(
    params: Params,
    section_kube_performance_cpu: Optional[PerformanceUsage],
    section_kube_cpu_resources: Optional[Resources],
    section_kube_allocatable_cpu_resource: Optional[AllocatableResource],
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
    section_kube_performance_cpu: Optional[PerformanceUsage],
    section_kube_cpu_resources: Optional[Resources],
    section_kube_allocatable_cpu_resource: Optional[AllocatableResource],
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
        CPU_RENDER_FUNC,
    )


register.agent_section(
    name="kube_performance_cpu_v1",
    parsed_section_name="kube_performance_cpu",
    parse_function=parse_performance_usage,
)


register.agent_section(
    name="kube_cpu_resources_v1",
    parsed_section_name="kube_cpu_resources",
    parse_function=parse_resources,
)

register.agent_section(
    name="kube_allocatable_cpu_resource_v1",
    parsed_section_name="kube_allocatable_cpu_resource",
    parse_function=parse_allocatable_resource,
)

register.check_plugin(
    name="kube_cpu",
    service_name="CPU resources",
    sections=["kube_performance_cpu", "kube_cpu_resources", "kube_allocatable_cpu_resource"],
    check_ruleset_name="kube_cpu",
    discovery_function=discovery_kube_cpu,
    check_function=check_kube_cpu,
    check_default_parameters=DEFAULT_PARAMS,
)
