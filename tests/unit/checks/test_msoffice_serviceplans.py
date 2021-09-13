#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from tests.testlib import Check

from .checktestlib import assertCheckResultsEqual, BasicCheckResult, CheckResult

# Mark all tests in this file as check related tests
pytestmark = pytest.mark.checks


@pytest.mark.parametrize(
    "params, expected_status, expected_levels_info",
    [
        ({}, 0, ""),
        ({"levels": (1, 3)}, 1, " (warn/crit at 1/3)"),
        ({"levels": (0, 1)}, 2, " (warn/crit at 0/1)"),
    ],
)
def test_check_win_license(params, expected_status, expected_levels_info):
    check = Check("msoffice_serviceplans")

    item = "bundle"
    output = check.run_check(
        item,
        params,
        [
            [item, "plan-success-1", "Success"],
            [item, "plan-suc", "cess-2", "Success"],
            [item, "plan-pending-1", "PendingActivation"],
            [item, "plan-pen", "ding-2", "PendingActivation"],
        ],
    )

    result = [
        BasicCheckResult(expected_status, "Success: 2, Pending: 2%s" % expected_levels_info),
        BasicCheckResult(0, "Pending Services: plan-pending-1, plan-pen ding-2"),
    ]

    assertCheckResultsEqual(
        CheckResult(output),
        CheckResult(result),
    )
