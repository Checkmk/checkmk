#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import json
from typing import Optional

from cmk.base.plugins.agent_based.utils.k8s import Memory
from cmk.base.plugins.agent_based.utils.kube_resources import (
    AllocatableResource,
    check_resource,
    DEFAULT_PARAMS,
    Params,
    parse_allocatable_resource,
    parse_resources,
    Resources,
    Usage,
)

from .agent_based_api.v1 import register, render, Service
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable


# TODO: Agent should return a section of the form:
# class ResourceUsage(BaseModel):
#     type_: Literal["memory", "cpu"]
#     usage: float
# this also should fix the line total_usage = usage.usage
def parse_performance_memory(string_table: StringTable) -> Usage:
    """
    >>> parse_performance_memory([['{"memory_usage_bytes": 18120704.0}']])
    Usage(usage=18120704.0)
    """
    memory = Memory(**json.loads(string_table[0][0]))
    return Usage(usage=memory.memory_usage_bytes)


register.agent_section(
    name="kube_memory_resources_v1",
    parse_function=parse_resources,
    parsed_section_name="kube_memory_resources",
)


register.agent_section(
    name="kube_performance_memory_v1",
    parse_function=parse_performance_memory,
    parsed_section_name="kube_performance_memory",
)


register.agent_section(
    name="kube_allocatable_memory_resource_v1",
    parsed_section_name="kube_allocatable_memory_resource",
    parse_function=parse_allocatable_resource,
)


def discovery_kube_memory(
    section_kube_performance_memory: Optional[Usage],
    section_kube_memory_resources: Optional[Resources],
    section_kube_allocatable_memory_resource: Optional[AllocatableResource],
) -> DiscoveryResult:
    yield Service()


def check_kube_memory(
    params: Params,
    section_kube_performance_memory: Optional[Usage],
    section_kube_memory_resources: Optional[Resources],
    section_kube_allocatable_memory_resource: Optional[AllocatableResource],
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


register.check_plugin(
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
