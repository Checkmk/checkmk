#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import time
from typing import Any, MutableMapping, Optional

from cmk.base.plugins.agent_based.utils.kube_resources import (
    check_resource_quota_resource,
    CPU_RENDER_FUNC,
    HardResourceRequirement,
    Params,
    parse_hard_requirements,
    parse_performance_usage,
    performance_cpu,
    RESOURCE_QUOTA_DEFAULT_PARAMS,
)

from .agent_based_api.v1 import get_value_store, register, Service
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult
from .utils.kube import PerformanceUsage

register.agent_section(
    name="kube_resource_quota_cpu_resources_v1",
    parse_function=parse_hard_requirements,
    parsed_section_name="kube_resource_quota_cpu_resources",
)


register.agent_section(
    name="kube_resource_quota_performance_cpu_v1",
    parse_function=parse_performance_usage,
    parsed_section_name="kube_resource_quota_performance_cpu",
)


def discovery_kube_resource_quota_cpu(
    section_kube_resource_quota_performance_cpu: Optional[PerformanceUsage],
    section_kube_resource_quota_cpu_resources: Optional[HardResourceRequirement],
) -> DiscoveryResult:
    yield Service()


def check_kube_resource_quota_cpu(
    params: Params,
    section_kube_resource_quota_performance_cpu: Optional[PerformanceUsage],
    section_kube_resource_quota_cpu_resources: Optional[HardResourceRequirement],
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
    section_kube_resource_quota_performance_cpu: Optional[PerformanceUsage],
    section_kube_resource_quota_cpu_resources: Optional[HardResourceRequirement],
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
        render_func=CPU_RENDER_FUNC,
    )


register.check_plugin(
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
