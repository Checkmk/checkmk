#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from testlib import Check  # type: ignore[import]

from cmk.base.api.agent_based.checking_classes import CheckResult
from cmk.base.plugins.agent_based.utils.esx_vsphere import Section


@pytest.mark.parametrize(
    "section, expected_check_result",
    [
        pytest.param(
            Section([
                ("summary.quickStats.overallMemoryUsage", ["322520"]),
                ("hardware.memorySize", ["1648903192576"]),
            ]),
            [
                0,
                "Usage: 20.51% - 314.96 GB of 1.50 TB",
                [
                    ("mem_used", 338186731520.0, None, None, 0, 1648903192576.0),
                    ("mem_total", 1648903192576.0),
                ],
            ],
            id=("Sunshine case"),
        )
    ],
)
@pytest.mark.usefixtures("config_load_all_checks")
def test_check_esx_vsphere_hostsystem_mem_usage(section: Section,
                                                expected_check_result: CheckResult) -> None:
    check = Check("esx_vsphere_hostsystem.mem_usage")
    assert list(check.run_check(None, {}, section)) == expected_check_result
