#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from tests.testlib import Check

from .checktestlib import CheckResult

pytestmark = pytest.mark.checks

# <<<mongodb_flushing>>>
# average_ms 1.28893335892
# last_ms 0
# flushed 36479


@pytest.mark.parametrize(
    "info,state_expected,info_expected,perf_expected,state_expected_flush,info_expected_flush,"
    "perf_expected_flush_key,perf_expected_flush_value",
    [
        (
            [("average_ms", "1.28893335892"), ("last_ms", "0"), ("flushed", "36479")],
            0,
            "Average flush time over 60 minutes: 0.00 ms",
            [],
            0,
            "Last flush time: 0.00 s",
            "flush_time",
            0.0,
        ),
        (
            [("average_ms", "5"), ("last_ms", "121"), ("flushed", "10000")],
            0,
            "Average flush time over 60 minutes: 0.00 ms",
            [],
            1,
            "Last flush time: 0.12 s (warn/crit at 0.10 s/0.20 s)",
            "flush_time",
            0.121,
        ),
        (
            [("last_ms", "120"), ("flushed", "10000")],
            3,
            "missing data: average_ms",
            [],
            -1,
            "",
            "",
            -1.0,
        ),
        (
            [("average_ms", "5"), ("flushed", "10000")],
            3,
            "missing data: last_ms",
            [],
            -1,
            "",
            "",
            -1.0,
        ),
        (
            [("average_ms", "5"), ("last_ms", "120")],
            3,
            "missing data: flushed",
            [],
            -1,
            "",
            "",
            -1.0,
        ),
        ([("last_ms", "120")], 3, "missing data: average_ms and flushed", [], -1, "", "", -1.0),
        ([], 3, "missing data: average_ms and flushed and last_ms", [], -1, "", "", -1.0),
    ],
)
def test_check_function(
    info,
    state_expected,
    info_expected,
    perf_expected,
    state_expected_flush,
    info_expected_flush,
    perf_expected_flush_key,
    perf_expected_flush_value,
):
    """
    Only checks for missing flushing data
    """
    check = Check("mongodb_flushing")
    check_result = CheckResult(
        check.run_check(None, {"average_time": (1, 4, 60), "last_time": (0.1, 0.2)}, info)
    )

    if len(check_result.subresults) == 1:
        check_result_3(check_result.subresults[0], state_expected, info_expected)
    elif len(check_result.subresults) == 4:
        check_result_average(check_result.subresults[0], state_expected, info_expected)
        check_result_flush_time(
            check_result.subresults[1],
            state_expected_flush,
            info_expected_flush,
            perf_expected_flush_key,
            perf_expected_flush_value,
        )


def check_result_3(result, state_expected, info_expected):
    assert result.status == state_expected
    assert result.infotext == info_expected


def check_result_average(result, state_expected, info_expected):
    assert result.status == state_expected
    assert result.infotext == info_expected


def check_result_flush_time(
    result,
    state_expected_flush,
    info_expected_flush,
    perf_expected_flush_key,
    perf_expected_flush_value,
):
    assert result.status == state_expected_flush
    assert result.infotext == info_expected_flush
    assert result.perfdata[0].key == perf_expected_flush_key
    assert result.perfdata[0].value == perf_expected_flush_value
