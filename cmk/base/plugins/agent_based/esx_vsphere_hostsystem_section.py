#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from .agent_based_api.v1 import register
from .agent_based_api.v1.type_defs import StringTable
from .utils.esx_vsphere import Section


def parse_esx_vsphere_hostsystem(string_table: StringTable) -> Section:
    """
    >>> from pprint import pprint
    >>> pprint(parse_esx_vsphere_hostsystem([
    ...     ['hardware.cpuInfo.numCpuCores', '12'],
    ...     ['hardware.cpuInfo.numCpuPackages', '2'],
    ...     ['hardware.cpuInfo.numCpuThreads', '24'],
    ...     ['hardware.cpuInfo.hz', '2933436846'],  # --> In Hz per CPU Core
    ...     ['summary.quickStats.overallCpuUsage', '7539'],  # --> In MHz
    ... ]))
    OrderedDict([('hardware.cpuInfo.numCpuCores', ['12']),
                 ('hardware.cpuInfo.numCpuPackages', ['2']),
                 ('hardware.cpuInfo.numCpuThreads', ['24']),
                 ('hardware.cpuInfo.hz', ['2933436846']),
                 ('summary.quickStats.overallCpuUsage', ['7539'])])

    """
    section = Section()
    # From what is being done in checks/esx_vsphere_hostsystem.cpu_util_cluster
    # it seems that the order of the keys must not be changed, or data will be lost
    # and/or scrambled up.
    for key, *value in string_table:
        section[key] = value
    return section


register.agent_section(
    name="esx_vsphere_hostsystem",
    parse_function=parse_esx_vsphere_hostsystem,
)
