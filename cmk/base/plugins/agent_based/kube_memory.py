#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import json
from typing import Mapping, Optional

from .agent_based_api.v1 import Metric, register, render, Result, Service, State
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable
from .utils.k8s import Memory
from .utils.kube import Resources
from .utils.memory import check_element, MemoryLevels


def parse_memory_resources(string_table: StringTable) -> Resources:
    return Resources(**json.loads(string_table[0][0]))


def parse_performance_memory(string_table: StringTable) -> Memory:
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


def discovery(section_kube_memory_resources, section_k8s_live_memory) -> DiscoveryResult:
    if section_kube_memory_resources:
        yield Service()


def _output_config_summaries(request: Optional[float], limits: Optional[float]):
    if request is None:
        request_summary = "no request value specified for at least one pod"
    else:
        request_summary = f"{render.bytes(request)}"

    if limits is None:
        limits_summary = "no limit value specified for at least one pod"
    else:
        limits_summary = f"{render.bytes(limits)}"

    yield Result(state=State.OK, summary=f"Configured Requests: {request_summary}")
    yield Result(state=State.OK, summary=f"Configured Limits: {limits_summary}")


def _render_absolute_metrics(usage: float, request: Optional[float], limits: Optional[float]):
    """Render metrics based on absolute values and display in same graph"""

    yield Metric("k8s_mem_used", usage)

    if request is not None:
        yield Metric("k8s_memory_request", request)

    if limits is not None:
        yield Metric("k8s_memory_limit", limits)


def _output_memory_usage(
    total_usage: float, limits: Optional[float], levels=Optional[MemoryLevels]
):
    if limits is None:
        yield Result(state=State.OK, summary=f"Usage: {render.bytes(total_usage)}")
        return

    result, metric = check_element(
        "Usage",
        used=total_usage,
        total=limits,
        levels=levels,
        create_percent_metric=True,
    )

    if not isinstance(result, Result):
        raise TypeError("usage result is not of type Result")

    if not isinstance(metric, Metric):
        raise TypeError("usage metric is not of type Metric")

    yield result
    yield Metric(
        name="k8s_mem_used_percent",
        value=metric.value,
        levels=metric.levels,
        boundaries=metric.boundaries,
    )


def check(
    params: Mapping[str, MemoryLevels],
    section_kube_memory_resources: Optional[Resources],
    section_k8s_live_memory: Optional[Memory],
) -> CheckResult:
    if not section_kube_memory_resources:
        return

    parsed_limit = None
    if isinstance(section_kube_memory_resources.limit, float):
        parsed_limit = section_kube_memory_resources.limit
    parsed_request = None
    if isinstance(section_kube_memory_resources.request, float):
        parsed_request = section_kube_memory_resources.request

    if section_k8s_live_memory:
        total_usage = section_k8s_live_memory.memory_usage_bytes
        yield from _output_memory_usage(
            total_usage=total_usage,
            limits=parsed_limit,
            levels=params.get("levels_ram"),
        )
        yield from _render_absolute_metrics(
            total_usage,
            parsed_request,
            parsed_limit,
        )

    yield from _output_config_summaries(parsed_request, parsed_limit)


register.check_plugin(
    name="kube_memory",
    service_name="Memory",
    sections=["kube_memory_resources", "k8s_live_memory"],
    discovery_function=discovery,
    check_function=check,
    check_ruleset_name="k8s_memory",
    check_default_parameters={"levels_ram": ("perc_used", (80.0, 90.0))},
)
