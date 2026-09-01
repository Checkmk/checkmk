#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import Metric, Result, Service, State
from cmk.legacy_checks.ddn_s2a_uptime import (
    check_ddn_s2a_uptime,
    discover_ddn_s2a_uptime,
    parse_ddn_s2a_uptime,
)

_STRING_TABLE = [
    [
        "0@8@uptime_years@1@uptime_days@2@uptime_hours@3@uptime_minutes@4@$",
    ],
]

# One year (counted as 365 days), two days, three hours and four minutes.
_UPTIME_SEC = 31719840


def test_discover_ddn_s2a_uptime() -> None:
    assert list(discover_ddn_s2a_uptime(parse_ddn_s2a_uptime(_STRING_TABLE))) == [Service()]


def test_check_ddn_s2a_uptime_without_levels() -> None:
    result, metric = check_ddn_s2a_uptime({}, parse_ddn_s2a_uptime(_STRING_TABLE))

    assert isinstance(result, Result)
    assert result.state is State.OK
    # The "Up since" part of the summary depends on the current time.
    assert result.summary.endswith(", uptime: 367 days, 3:04:00")
    assert metric == Metric("uptime", _UPTIME_SEC)


def test_check_ddn_s2a_uptime_above_max() -> None:
    result, _metric = check_ddn_s2a_uptime({"max": (60, 120)}, parse_ddn_s2a_uptime(_STRING_TABLE))

    assert isinstance(result, Result)
    assert result.state is State.CRIT
    assert result.summary.endswith(", uptime: 367 days, 3:04:00 (warn/crit at 0:01:00/0:02:00)")
