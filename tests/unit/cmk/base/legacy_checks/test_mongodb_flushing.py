#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"

import pytest

from cmk.base.legacy_checks.mongodb_flushing import check_mongodb_flushing, parse_mongodb_flushing

# <<<mongodb_flushing>>>
# average_ms 1.28893335892
# last_ms 0
# flushed 36479


@pytest.mark.usefixtures("initialised_item_state")
@pytest.mark.parametrize(
    "info,state_expected,info_expected,perf_expected,state_expected_flush,info_expected_flush,"
    "perf_expected_flush_key,perf_expected_flush_value",
    [
        (
            [("average_ms", "1.28893335892"), ("last_ms", "0"), ("flushed", "36479")],
            0,
            "Average flush time over 60 minutes: 0.0 ms",
            [],
            0,
            "Last flush time: 0.00 s",
            "flush_time",
            0.0,
        ),
        (
            [("average_ms", "5"), ("last_ms", "121"), ("flushed", "10000")],
            2,
            "Average flush time over 60 minutes: 121.0 ms (warn/crit at 1.0 ms/4.0 ms)",
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
    check_result = list(
        check_mongodb_flushing(
            None,
            {"average_time": (1, 4, 60), "last_time": (0.1, 0.2)},
            parse_mongodb_flushing(info),
        )
    )

    assert check_result[0][:2] == (state_expected, info_expected)
    if len(check_result) == 1:
        return

    assert check_result[1] == (
        state_expected_flush,
        info_expected_flush,
        [(perf_expected_flush_key, perf_expected_flush_value, 0.1, 0.2)],
    )
