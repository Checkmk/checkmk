#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Any, Mapping

from .agent_based_api.v1 import Metric, register, Service
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult
from .utils.esx_vsphere import Section
from .utils.memory import check_element


def discover_esx_vsphere_hostsystem_mem_usage(section: Section) -> DiscoveryResult:
    if 'summary.quickStats.overallMemoryUsage' in section and 'hardware.memorySize' in section:
        yield Service()


def check_esx_vsphere_hostsystem_mem_usage(
    params: Mapping[str, Any],
    section: Section,
) -> CheckResult:

    if "summary.quickStats.overallMemoryUsage" not in section or 'hardware.memorySize' not in section:
        return

    try:
        memory_usage = float(section['summary.quickStats.overallMemoryUsage'][0]) * 1024 * 1024
        memory_size = float(section['hardware.memorySize'][0])
    except (IndexError, ValueError):
        return

    yield from check_element(
        "Usage",
        memory_usage,
        memory_size,
        ('perc_used', params['levels_upper']),
        metric_name="mem_used",
    )
    yield Metric('mem_total', memory_size)


register.check_plugin(
    name="esx_vsphere_hostsystem_mem_usage",
    service_name="Memory",
    sections=["esx_vsphere_hostsystem"],
    discovery_function=discover_esx_vsphere_hostsystem_mem_usage,
    check_function=check_esx_vsphere_hostsystem_mem_usage,
    check_default_parameters={'levels_upper': (80.0, 90.0)},
    check_ruleset_name="esx_host_memory",
)
