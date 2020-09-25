#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Any, Dict, List, Optional

from .agent_based_api.v1.type_defs import (
    CheckResult,
    DiscoveryResult,
    Parameters,
)
from .agent_based_api.v1 import get_value_store, register, Result, Service, State as state
from .utils import cpu_util


def discover_esx_vsphere_hostsystem_cpu_usage(
    section_esx_vsphere_hostsystem: Dict[str, List[str]],
    section_winperf_processor: Any,
) -> DiscoveryResult:
    if section_winperf_processor:
        return

    required_keys = {
        'summary.quickStats.overallCpuUsage',
        'hardware.cpuInfo.hz',
        'hardware.cpuInfo.numCpuCores',
    }
    if required_keys.issubset(section_esx_vsphere_hostsystem.keys()):
        yield Service()


def check_esx_vsphere_hostsystem_cpu(
    params: Parameters,
    section_esx_vsphere_hostsystem: Optional[Dict[str, List[str]]],
    section_winperf_processor: Any,
) -> CheckResult:
    if not section_esx_vsphere_hostsystem:
        return
    try:
        num_sockets = int(section_esx_vsphere_hostsystem['hardware.cpuInfo.numCpuPackages'][0])
        num_cores = int(section_esx_vsphere_hostsystem['hardware.cpuInfo.numCpuCores'][0])
        num_threads = int(section_esx_vsphere_hostsystem['hardware.cpuInfo.numCpuThreads'][0])
        used_mhz = float(section_esx_vsphere_hostsystem['summary.quickStats.overallCpuUsage'][0])
        mhz_per_core = float(section_esx_vsphere_hostsystem['hardware.cpuInfo.hz'][0]) * 1e-6
    except KeyError:
        return

    total_mhz = mhz_per_core * num_cores
    usage = used_mhz / total_mhz * 100

    yield from cpu_util.check_cpu_util(get_value_store(), usage, params)
    yield Result(
        state=state.OK,
        summary="%.2fGHz/%.2fGHz" % (used_mhz / 1000.0, total_mhz / 1000.0),
    )
    yield Result(
        state=state.OK,
        summary="Sockets: %d" % num_sockets,
    )
    yield Result(
        state=state.OK,
        summary="Cores/socket: %d" % int(num_cores / num_sockets),
    )
    yield Result(
        state=state.OK,
        summary="Threads: %d" % num_threads,
    )


register.check_plugin(
    name="esx_vsphere_hostsystem_cpu_usage",
    service_name="CPU utilization",
    sections=["esx_vsphere_hostsystem", "winperf_processor"],
    discovery_function=discover_esx_vsphere_hostsystem_cpu_usage,
    check_function=check_esx_vsphere_hostsystem_cpu,
    check_default_parameters={},
    check_ruleset_name="cpu_utilization_os",
)
