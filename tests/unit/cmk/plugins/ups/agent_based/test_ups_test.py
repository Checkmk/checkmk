#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.agent_based.v2 import Result, Service, State
from cmk.plugins.ups.agent_based.ups_test import check_ups_test, discover_ups_test

check_name = "ups_test"

_DAYS = 3600 * 24

DEFAULT_PARAMS = {"levels_elapsed_time": ("no_levels", None)}
PARAMS = {"levels_elapsed_time": ("fixed", (2 * _DAYS, 3 * _DAYS))}


def test_discover_nothing() -> None:
    assert not list(discover_ups_test([[["3600"]], []]))


def test_discover() -> None:
    assert list(discover_ups_test([[["3600"]], [["1", "15000000", ""]]])) == [Service()]


@pytest.mark.parametrize(
    "raw_state, state, summary",
    [
        ("1", State.OK, "Last test: passed (details)"),
        ("2", State.WARN, "Last test: warning (details)"),
        ("3", State.CRIT, "Last test: error (details)"),
        ("4", State.CRIT, "Last test: aborted (details)"),
        ("5", State.OK, "Last test: in progress (details)"),
        ("6", State.OK, "Last test: no tests initiated (details)"),
    ],
)
def test_check_ups_test_result_details(raw_state: str, state: State, summary: str) -> None:
    result, *_ = check_ups_test(DEFAULT_PARAMS, [[["7200"]], [[raw_state, "3600", "details"]]])
    assert result == Result(state=state, summary=summary)


def test_check_ups_test_time_check_no_start_time() -> None:
    _, result, *_ = check_ups_test(DEFAULT_PARAMS, [[["0"]], [["1", "0", ""]]])
    assert isinstance(result, Result)
    assert result.state is State.OK
    assert result.summary.startswith("No battery test since start of device")


def test_check_ups_test_time_check_start_time_warn() -> None:
    _, result, *_ = check_ups_test(PARAMS, [[[str(360000 * 52)]], [["1", "1000", ""]]])
    assert isinstance(result, Result)
    assert result.state is State.WARN
    assert result.summary.startswith("Time since start of last test: 2 days 3 hours")


def test_check_ups_test_time_check_negative_elapsed_time() -> None:
    _, result, *_ = check_ups_test(PARAMS, [[["1000"]], [["1", "2000", ""]]])
    assert isinstance(result, Result)
    assert result.state is State.UNKNOWN
    assert result.summary.startswith("Could not determine time since start of last test")


def test_ups_test_unknown_test_result() -> None:
    check_results = list(
        check_ups_test(DEFAULT_PARAMS, [[["2400776998"]], [["0", "0", "aardvark"]]])
    )
    assert check_results[0] == Result(state=State.UNKNOWN, summary="Last test: unknown (aardvark)")
