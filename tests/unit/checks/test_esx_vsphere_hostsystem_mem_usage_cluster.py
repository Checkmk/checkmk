#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from contextlib import suppress
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
                ("name", ["bli.bla.com"]),
                ("hardware.memorySize", ["1648903192576"]),
                ("summary.quickStats.overallMemoryUsage", ["322520"]),
            ]),
            [],
            (
                0,
                "Usage: 20.51% - 314.96 GB of 1.50 TB",
                [
                    ("mem_used", 338186731520.0, None, None, 0, 1648903192576.0),
                    ("mem_total", 1648903192576.0),
                ],
            ),
            id=("Mem usage 1 node without params"),
        ),
        pytest.param(
            Section([
                ("name", ["bli.bla.com"]),
                ("hardware.memorySize", ["1648903192576"]),
                ("summary.quickStats.overallMemoryUsage", ["322520"]),
            ]),
            [(0, (80.0, 90.0))],
            (
                0,
                "Usage: 20.51% - 314.96 GB of 1.50 TB",
                [
                    (
                        "mem_used",
                        338186731520.0,
                        1319122554060.8,
                        1484012873318.4001,
                        0,
                        1648903192576.0,
                    ),
                    ("mem_total", 1648903192576.0),
                ],
            ),
            id=("Mem usage 1 node with params"),
        ),
    ],
)
@pytest.mark.usefixtures("config_load_all_checks")
def test_check_esx_vsphere_hostsystem_mem_usage_cluster(
    section: Section,
    params: Sequence[Tuple[int, Tuple[float, float]]],
    expected_check_result: CheckResult,
):
    check = Check("esx_vsphere_hostsystem.mem_usage_cluster")
    assert check.run_check(None, params, section) == expected_check_result
