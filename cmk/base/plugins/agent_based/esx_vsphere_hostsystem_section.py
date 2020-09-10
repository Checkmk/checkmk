#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Dict, List

from .agent_based_api.v1.type_defs import AgentStringTable
from .agent_based_api.v1 import register

Section = Dict[str, List[str]]


def parse_esx_vsphere_hostsystem(string_table: AgentStringTable) -> Section:
    """
        >>> from pprint import pprint
        >>> pprint(parse_esx_vsphere_hostsystem([
        ...     ['hardware.cpuInfo.numCpuCores', '12'],
        ...     ['hardware.cpuInfo.numCpuPackages', '2'],
        ...     ['hardware.cpuInfo.numCpuThreads', '24'],
        ...     ['hardware.cpuInfo.hz', '2933436846'],  # --> In Hz per CPU Core
        ...     ['summary.quickStats.overallCpuUsage', '7539'],  # --> In MHz
        ... ]))
        {'hardware.cpuInfo.hz': ['2933436846'],
         'hardware.cpuInfo.numCpuCores': ['12'],
         'hardware.cpuInfo.numCpuPackages': ['2'],
         'hardware.cpuInfo.numCpuThreads': ['24'],
         'summary.quickStats.overallCpuUsage': ['7539']}
    """
    section = {}
    for key, *value in string_table:
        section[key] = value
    return section


register.agent_section(
    name="esx_vsphere_hostsystem",
    parse_function=parse_esx_vsphere_hostsystem,
)
