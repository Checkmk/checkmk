#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Sequence, Tuple

import pytest

from testlib import Check  # type: ignore[import]

from cmk.base.api.agent_based.checking_classes import CheckResult
from cmk.base.plugins.agent_based.utils.esx_vsphere import Section


@pytest.mark.parametrize(
    "section, params, expected_check_result",
    [
        pytest.param(
            Section([
                ("hardware.cpuInfo.numCpuCores", ["36"]),
                ("hardware.cpuInfo.numCpuPackages", ["2"]),
                ("hardware.cpuInfo.numCpuThreads", ["72"]),
                ("hardware.cpuInfo.hz", ["3092733850"]),
                ("summary.quickStats.overallCpuUsage", ["597"]),
            ]),
            [],
            [
                (
                    0,
                    "Total CPU: 0.56%",
                    [("util", 0.5622496527896615, None, None, 0, 100)],
                ),
                (0, "1 Nodes"),
                (0, "0.58GHz/103.69GHz"),
                (0, "72 threads"),
            ],
            id=("CPU util without params"),
        ),
        pytest.param(
            Section([
                ("hardware.cpuInfo.numCpuCores", ["36"]),
                ("hardware.cpuInfo.numCpuPackages", ["2"]),
                ("hardware.cpuInfo.numCpuThreads", ["72"]),
                ("hardware.cpuInfo.hz", ["3092733850"]),
                ("summary.quickStats.overallCpuUsage", ["597"]),
            ]),
            [(0, (90.0, 95.0))],
            [
                (
                    0,
                    "Total CPU: 0.56%",
                    [("util", 0.5622496527896615, 90.0, 95.0, 0, 100)],
                ),
                (0, "1 Nodes"),
                (0, "0.58GHz/103.69GHz"),
                (0, "72 threads"),
            ],
            id=("CPU util with params"),
        ),
    ],
)
@pytest.mark.usefixtures("config_load_all_checks")
def test_check_esx_vsphere_hostsystem_cpu_usage(
    section: Section,
    params: Sequence[Tuple[int, Tuple[float, float]]],
    expected_check_result: CheckResult,
) -> None:
    check = Check("esx_vsphere_hostsystem.cpu_util_cluster")
    assert list(check.run_check(None, params, section)) == expected_check_result
