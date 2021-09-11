#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Any, Mapping, NamedTuple, Optional

from .agent_based_api.v1 import Metric, register, Result, Service, State
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult
from .utils.esx_vsphere import Section
from .utils.memory import check_element


class EsxHostsystemMemory(NamedTuple):
    usage: float
    size: float


def discover_esx_vsphere_hostsystem_mem_usage(section: Section) -> DiscoveryResult:
    if "summary.quickStats.overallMemoryUsage" in section and "hardware.memorySize" in section:
        yield Service()


def _parse_mem_values(section: Section) -> Optional[EsxHostsystemMemory]:
    try:
        memory_usage = float(section["summary.quickStats.overallMemoryUsage"][0]) * 1024 * 1024
        memory_size = float(section["hardware.memorySize"][0])
    except (KeyError, IndexError, ValueError):
        return None

    return EsxHostsystemMemory(memory_usage, memory_size)


def _check_esx_vsphere_hostsystem_mem_usage_common(
    params: Mapping[str, Any],
    memory_section: EsxHostsystemMemory,
) -> CheckResult:
    yield from check_element(
        "Usage",
        memory_section.usage,
        memory_section.size,
        ("perc_used", params["levels_upper"]),
        metric_name="mem_used",
    )
    yield Metric("mem_total", memory_section.size)


def check_esx_vsphere_hostsystem_mem_usage(
    params: Mapping[str, Any],
    section: Section,
) -> CheckResult:

    if (
        "summary.quickStats.overallMemoryUsage" not in section
        or "hardware.memorySize" not in section
    ):
        return

    memory_section = _parse_mem_values(section)

    if memory_section is None:
        return

    yield from _check_esx_vsphere_hostsystem_mem_usage_common(params, memory_section)


def _applicable_params(params: Mapping[str, Any], node_count: int) -> Mapping[str, Any]:
    if "cluster" not in params:
        return params

    for count, applicable_params in sorted(params["cluster"], reverse=True):
        if node_count >= count:
            return applicable_params

    return params


def cluster_check_esx_vsphere_hostsystem_mem_usage(
    params: Mapping[str, Any],
    section: Mapping[str, Optional[Section]],
) -> CheckResult:

    aggregated_section = None
    for node_section in section.values():
        if node_section and (memory := _parse_mem_values(node_section)):
            aggregated_section = [
                sum(s)
                for s in zip(
                    aggregated_section or [0.0, 0.0],
                    memory,
                )
            ]

    if not aggregated_section:
        return

    node_count = len(section)
    yield Result(state=State.OK, summary=f"{node_count} nodes")

    yield from _check_esx_vsphere_hostsystem_mem_usage_common(
        _applicable_params(params, node_count),
        EsxHostsystemMemory(*aggregated_section),
    )


register.check_plugin(
    name="esx_vsphere_hostsystem_mem_usage",
    service_name="Memory",
    sections=["esx_vsphere_hostsystem"],
    discovery_function=discover_esx_vsphere_hostsystem_mem_usage,
    check_function=check_esx_vsphere_hostsystem_mem_usage,
    cluster_check_function=cluster_check_esx_vsphere_hostsystem_mem_usage,
    check_default_parameters={"levels_upper": (80.0, 90.0)},
    check_ruleset_name="esx_host_memory",
)
