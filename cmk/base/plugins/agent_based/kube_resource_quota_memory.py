#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Optional

from cmk.base.plugins.agent_based.utils.kube_resources import (
    check_resource_quota_resource,
    HardResourceRequirement,
    Params,
    parse_hard_requirements,
    parse_performance_usage,
    RESOURCE_QUOTA_DEFAULT_PARAMS,
)

from .agent_based_api.v1 import register, render, Service
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult
from .utils.kube import PerformanceUsage

register.agent_section(
    name="kube_resource_quota_memory_resources_v1",
    parse_function=parse_hard_requirements,
    parsed_section_name="kube_resource_quota_memory_resources",
)


register.agent_section(
    name="kube_resource_quota_performance_memory_v1",
    parse_function=parse_performance_usage,
    parsed_section_name="kube_resource_quota_performance_memory",
)


def discovery_kube_resource_quota_memory(
    section_kube_resource_quota_performance_memory: Optional[PerformanceUsage],
    section_kube_resource_quota_memory_resources: Optional[HardResourceRequirement],
) -> DiscoveryResult:
    yield Service()


def check_kube_resource_quota_memory(
    params: Params,
    section_kube_resource_quota_performance_memory: Optional[PerformanceUsage],
    section_kube_resource_quota_memory_resources: Optional[HardResourceRequirement],
) -> CheckResult:
    yield from check_resource_quota_resource(
        params=params,
        resource_usage=section_kube_resource_quota_performance_memory,
        hard_requirement=section_kube_resource_quota_memory_resources,
        resource_type="memory",
        render_func=render.bytes,
    )


register.check_plugin(
    name="kube_resource_quota_memory",
    service_name="Resource quota memory resources",
    sections=[
        "kube_resource_quota_performance_memory",
        "kube_resource_quota_memory_resources",
    ],
    discovery_function=discovery_kube_resource_quota_memory,
    check_function=check_kube_resource_quota_memory,
    check_ruleset_name="kube_resource_quota_memory",
    check_default_parameters=RESOURCE_QUOTA_DEFAULT_PARAMS,
)
