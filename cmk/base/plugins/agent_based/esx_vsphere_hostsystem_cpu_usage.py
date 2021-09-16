#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from typing import Any, List, Mapping, NamedTuple, Optional

from .agent_based_api.v1 import get_value_store, register, render, Result, Service, State
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult
from .utils import cpu_util
from .utils.esx_vsphere import Section


class EsxVsphereHostsystemCpuSection(NamedTuple):
    num_sockets: int
    num_cores: int
    num_threads: int
    used_mhz: float
    mhz_per_core: float


def extract_esx_vsphere_hostsystem_cpu_usage(
    section: Section,
) -> Optional[EsxVsphereHostsystemCpuSection]:
    try:
        return EsxVsphereHostsystemCpuSection(
            num_sockets=int(section["hardware.cpuInfo.numCpuPackages"][0]),
            num_cores=int(section["hardware.cpuInfo.numCpuCores"][0]),
            num_threads=int(section["hardware.cpuInfo.numCpuThreads"][0]),
            used_mhz=float(section["summary.quickStats.overallCpuUsage"][0]),
            mhz_per_core=float(section["hardware.cpuInfo.hz"][0]),
        )
    except (KeyError, ValueError):
        return None


def discover_esx_vsphere_hostsystem_cpu_usage(
    section_esx_vsphere_hostsystem: Optional[Section],
    section_winperf_processor: Optional[List],  # currently no parse function
) -> DiscoveryResult:
    if section_winperf_processor or not section_esx_vsphere_hostsystem:
        return

    required_keys = {
        "summary.quickStats.overallCpuUsage",
        "hardware.cpuInfo.hz",
        "hardware.cpuInfo.numCpuCores",
    }
    if required_keys.issubset(section_esx_vsphere_hostsystem.keys()):
        yield Service()


def _check_esx_vsphere_hostsystem_cpu_usage_common(
    params: Mapping[str, Any],
    cpu_section: EsxVsphereHostsystemCpuSection,
    total_mhz: float,
) -> CheckResult:

    yield from cpu_util.check_cpu_util(
        util=cpu_section.used_mhz / total_mhz * 100,
        params=params,
        value_store=get_value_store(),
        this_time=time.time(),
    )
    yield Result(
        state=State.OK,
        notice="%s/%s"
        % (
            render.frequency(cpu_section.used_mhz * 1e6),
            render.frequency(total_mhz * 1e6),
        ),
    )
    yield Result(
        state=State.OK,
        notice="Sockets: %d" % cpu_section.num_sockets,
    )
    yield Result(
        state=State.OK,
        notice="Cores/socket: %d" % int(cpu_section.num_cores / cpu_section.num_sockets),
    )
    yield Result(
        state=State.OK,
        notice="Threads: %d" % cpu_section.num_threads,
    )


def check_esx_vsphere_hostsystem_cpu_usage(
    params: Mapping[str, Any],
    section_esx_vsphere_hostsystem: Optional[Section],
    section_winperf_processor: Optional[List],
) -> CheckResult:
    if not section_esx_vsphere_hostsystem:
        return

    cpu_section = extract_esx_vsphere_hostsystem_cpu_usage(section_esx_vsphere_hostsystem)
    if not cpu_section:
        return

    yield from _check_esx_vsphere_hostsystem_cpu_usage_common(
        params,
        cpu_section,
        cpu_section.mhz_per_core * 1e-6 * cpu_section.num_cores,
    )


def _applicable_thresholds(
    params: Mapping[str, Any],
    num_nodes: int,
) -> Mapping[str, Any]:
    for nodes, thresholds in sorted(params.get("cluster", []), reverse=True):
        if num_nodes >= nodes:
            return thresholds

    return params


def cluster_check_esx_vsphere_hostsystem_cpu_usage(
    params: Mapping[str, Any],
    section_esx_vsphere_hostsystem: Mapping[str, Optional[Section]],
    section_winperf_processor: Mapping[str, Optional[List]],
) -> CheckResult:

    aggregated_section = None
    total_mhz = 0.0
    for _node, section in section_esx_vsphere_hostsystem.items():
        if section and (cpu_section := extract_esx_vsphere_hostsystem_cpu_usage(section)):
            total_mhz += cpu_section.mhz_per_core * 1e-6 * cpu_section.num_cores
            aggregated_section = [
                sum(s)
                for s in zip(
                    aggregated_section or [0, 0, 0, 0, 0.0, 0.0],
                    cpu_section,
                )
            ]

    if not aggregated_section:
        return

    num_nodes = len(section_esx_vsphere_hostsystem)
    yield Result(state=State.OK, summary=f"{num_nodes} nodes")

    yield from _check_esx_vsphere_hostsystem_cpu_usage_common(
        _applicable_thresholds(params, num_nodes),
        EsxVsphereHostsystemCpuSection(
            num_sockets=int(aggregated_section[0]),
            num_cores=int(aggregated_section[1]),
            num_threads=int(aggregated_section[2]),
            used_mhz=float(aggregated_section[3]),
            mhz_per_core=float(aggregated_section[4]),
        ),
        total_mhz,
    )


register.check_plugin(
    name="esx_vsphere_hostsystem_cpu_usage",
    service_name="CPU utilization",
    sections=["esx_vsphere_hostsystem", "winperf_processor"],
    discovery_function=discover_esx_vsphere_hostsystem_cpu_usage,
    check_function=check_esx_vsphere_hostsystem_cpu_usage,
    cluster_check_function=cluster_check_esx_vsphere_hostsystem_cpu_usage,
    check_default_parameters={},
    check_ruleset_name="cpu_utilization_esx_vsphere_hostsystem",
)
