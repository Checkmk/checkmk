#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections import OrderedDict

import pytest

from cmk.agent_based.v2 import StringTable
from cmk.plugins.vsphere.agent_based.esx_vsphere_hostsystem_section import (
    parse_esx_vsphere_hostsystem,
)
from cmk.plugins.vsphere.lib.esx_vsphere import Section


@pytest.mark.parametrize(
    "string_table, section",
    [
        (
            [
                ["hardware.cpuInfo.hz", "2199999776"],
                ["hardware.cpuInfo.numCpuCores", "20"],
                ["hardware.cpuInfo.numCpuPackages", "2"],
                ["hardware.cpuInfo.numCpuThreads", "40"],
                ["summary.quickStats.overallCpuUsage", "531"],
            ],
            OrderedDict(
                {
                    "hardware.cpuInfo.hz": ["2199999776"],
                    "hardware.cpuInfo.numCpuCores": ["20"],
                    "hardware.cpuInfo.numCpuPackages": ["2"],
                    "hardware.cpuInfo.numCpuThreads": ["40"],
                    "summary.quickStats.overallCpuUsage": ["531"],
                }
            ),
        ),
    ],
)
def test_parse_esx_vsphere_hostsystem(string_table: StringTable, section: Section) -> None:
    assert parse_esx_vsphere_hostsystem(string_table) == section
