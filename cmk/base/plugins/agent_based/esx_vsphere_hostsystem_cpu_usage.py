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
        section: Section) -> Optional[EsxVsphereHostsystemCpuSection]:
    try:
        return EsxVsphereHostsystemCpuSection(*[
            type_(section[key][0]) for key, type_ in [
                ('hardware.cpuInfo.numCpuPackages', int),
                ('hardware.cpuInfo.numCpuCores', int),
                ('hardware.cpuInfo.numCpuThreads', int),
                ('summary.quickStats.overallCpuUsage', float),
                ('hardware.cpuInfo.hz', float),
            ]
        ])
    except (KeyError, ValueError):
        return None


def discover_esx_vsphere_hostsystem_cpu_usage(
        section_esx_vsphere_hostsystem: Optional[Section],
        section_winperf_processor: Optional[List],  # currently no parse function
) -> DiscoveryResult:
    if section_winperf_processor or not section_esx_vsphere_hostsystem:
        return

    required_keys = {
        'summary.quickStats.overallCpuUsage',
        'hardware.cpuInfo.hz',
        'hardware.cpuInfo.numCpuCores',
    }
    if required_keys.issubset(section_esx_vsphere_hostsystem.keys()):
        yield Service()


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

    total_mhz = cpu_section.mhz_per_core * 1e-6 * cpu_section.num_cores
    usage = cpu_section.used_mhz / total_mhz * 100

    yield from cpu_util.check_cpu_util(
        util=usage,
        params=params,
        value_store=get_value_store(),
        this_time=time.time(),
    )
    yield Result(
        state=State.OK,
        notice="%s/%s" % (
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


register.check_plugin(
    name="esx_vsphere_hostsystem_cpu_usage",
    service_name="CPU utilization",
    sections=["esx_vsphere_hostsystem", "winperf_processor"],
    discovery_function=discover_esx_vsphere_hostsystem_cpu_usage,
    check_function=check_esx_vsphere_hostsystem_cpu_usage,
    check_default_parameters={},
    check_ruleset_name="cpu_utilization_os",
)
