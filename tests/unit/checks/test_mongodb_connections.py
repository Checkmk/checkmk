#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from tests.testlib import Check

from .checktestlib import CheckResult

pytestmark = pytest.mark.checks


@pytest.mark.parametrize(
    "info,state_expected,info_expected,perf_expected_key,perf_expected_value,state_expected_perc,info_expected_perc",
    [
        (
            [("current", "1"), ("available", "1"), ("totalCreated", "1")],
            0,
            "Used connections: 1",
            "connections",
            1,
            0,
            "Used percentage: 50.00%",
        ),
        (
            [("current", "10"), ("available", "200"), ("totalCreated", "25007")],
            0,
            "Used connections: 10",
            "connections",
            10,
            0,
            "Used percentage: 4.76%",
        ),
        (
            [("current", 1.1), ("available", "1"), ("totalCreated", "1")],
            0,
            "Used connections: 1",
            "connections",
            1,
            0,
            "Used percentage: 50.00%",
        ),
        (
            [("current", "10"), ("available", 200.1), ("totalCreated", "25007")],
            0,
            "Used connections: 10",
            "connections",
            10,
            0,
            "Used percentage: 4.76%",
        ),
        (
            [("current", "10"), ("available", "200"), ("totalCreated", 25007.1)],
            0,
            "Used connections: 10",
            "connections",
            10,
            0,
            "Used percentage: 4.76%",
        ),
        ([("current", "a"), ("available", "10"), ("totalCreated", "257")], 3, "", "", -1, -1, ""),
        ([("current", "1"), ("available", "a"), ("totalCreated", "257")], 3, "", "", -1, -1, ""),
        ([("current", "1"), ("available", "10"), ("totalCreated", "a")], 3, "", "", -1, -1, ""),
        ([("current", ""), ("available", "10"), ("totalCreated", "10000")], 3, "", "", -1, -1, ""),
        ([("current", "1"), ("available", ""), ("totalCreated", "10000")], 3, "", "", -1, -1, ""),
        ([("current", "1"), ("available", "10"), ("totalCreated", "")], 3, "", "", -1, -1, ""),
        (
            [("current", None), ("available", "10"), ("totalCreated", "10000")],
            3,
            "",
            "",
            -1,
            -1,
            "",
        ),
        ([("current", "1"), ("available", None), ("totalCreated", "10000")], 3, "", "", -1, -1, ""),
        ([("current", "1"), ("available", "10"), ("totalCreated", None)], 3, "", "", -1, -1, ""),
    ],
)
def test_check_function(
    info,
    state_expected,
    info_expected,
    perf_expected_key,
    perf_expected_value,
    state_expected_perc,
    info_expected_perc,
):
    """
    Checks funny connections values
    """
    check = Check("mongodb_connections")
    check_result = CheckResult(check.run_check(None, {"levels_perc": (80.0, 90.0)}, info))

    if len(check_result.subresults) == 0:
        assert state_expected == 3
    elif len(check_result.subresults) == 3:
        check_used_connection(
            check_result.subresults[0],
            state_expected,
            info_expected,
            perf_expected_key,
            perf_expected_value,
        )
        check_used_percentage(check_result.subresults[1], state_expected_perc, info_expected_perc)
        # check_used_rate(check_result.subresults[2]....  we are not testing the get_rate function here assuming it works
    else:
        raise AssertionError()


def check_used_connection(
    result, state_expected, info_expected, perf_expected_key, perf_expected_value
):
    assert result.status == state_expected
    assert result.infotext == info_expected
    assert result.perfdata[0].key == perf_expected_key
    assert result.perfdata[0].value == perf_expected_value


def check_used_percentage(result, state_expected_perc, info_expected_perc):
    assert result.status == state_expected_perc
    assert result.infotext == info_expected_perc
    assert len(result.perfdata) == 0
