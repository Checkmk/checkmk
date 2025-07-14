#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Mapping

import pytest

from cmk.agent_based.v2 import (
    CheckResult,
    DiscoveryResult,
    Metric,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.meinberg.agent_based.mbg_lantime_ng_refclock import (
    check_lantime_ng_refclock,
    check_lantime_ng_refclock_gps,
    discover_lantime_ng_refclock,
    discover_lantime_ng_refclock_gps,
)

pytestmark = pytest.mark.checks

meinberg_lantime_1 = [["1", "14", "3", "2", "3", "0", "12", "0", "0", "0", "2012-06-30"]]
meinberg_lantime_2 = [["1", "28", "3", "1", "52", "62", "100", "101", "127", "0", "0"]]
meinberg_lantime_5 = [["1", "14", "3", "1", "150", "6", "8", "0", "0", "1", "not announced"]]
meinberg_lantime_6 = [["1", "30", "3", "1", "155", "0", "8", "0", "0", "0", "2016-12-31"]]
meinberg_lantime_7 = [["1", "15", "3", "2", "101", "0", "0", "0", "0", "0", "not announced"]]
meinberg_lantime_8 = [["1", "999", "3", "1", "1", "10", "13", "0", "0", "0", "not announced"]]


@pytest.mark.parametrize(
    "info,expected",
    [
        (meinberg_lantime_1, []),  # GPS clocks are not covered here
        (meinberg_lantime_2, [Service(item="1")]),
        (meinberg_lantime_7, [Service(item="1")]),
        (meinberg_lantime_8, []),
    ],
)
def test_discovery_mbg_lantime_ng_refclock(info: StringTable, expected: DiscoveryResult) -> None:
    discovery = list(discover_lantime_ng_refclock(info))
    assert discovery == expected


@pytest.mark.parametrize(
    "info,item,expected",
    [
        (
            meinberg_lantime_2,
            "1",
            [
                Result(
                    state=State.OK,
                    summary="Type: pzf600, Usage: primary, State: synchronized (LW sync)",
                ),
                Result(state=State.OK, summary="Field strength: 80%"),
                Metric(name="field_strength", value=80.0),
                Result(state=State.OK, summary="Correlation: 62%"),
                Metric(name="correlation", value=62.0),
            ],
        ),
        (
            meinberg_lantime_7,
            "1",
            [
                Result(
                    state=State.WARN,
                    summary="Type: tcr511, Usage: primary, State: not synchronized (TCT sync)",
                )
            ],
        ),
    ],
)
def test_check_mbg_lantime_ng_refclock(info: StringTable, item: str, expected: CheckResult) -> None:
    result = list(check_lantime_ng_refclock(item, info))
    assert expected == result


@pytest.mark.parametrize(
    "info,expected",
    [
        (meinberg_lantime_1, [Service(item="1")]),
        (meinberg_lantime_2, []),  # don't discover GPS clocks
        (meinberg_lantime_5, [Service(item="1")]),
        (meinberg_lantime_6, [Service(item="1")]),
        (meinberg_lantime_7, []),
        (meinberg_lantime_8, []),
    ],
)
def test_discovery_mbg_lantime_ng_refclock_gps(
    info: StringTable, expected: DiscoveryResult
) -> None:
    discovery = list(discover_lantime_ng_refclock_gps(info))
    assert discovery == expected


@pytest.mark.parametrize(
    "info,item,params,expected",
    [
        (
            meinberg_lantime_1,
            "1",
            {"levels_lower": ("fixed", (3, 3))},
            [
                Result(
                    state=State.WARN,
                    summary="Type: gps170, Usage: primary, State: not synchronized (GPS antenna disconnected)",
                ),
                Result(state=State.OK, summary="Next leap second: 2012-06-30"),
                Result(state=State.CRIT, summary="Satellites (total: 12): 0 (warn/crit below 3/3)"),
            ],
        ),
        (
            meinberg_lantime_5,
            "1",
            {"levels_lower": ("fixed", (3, 3))},
            [
                Result(
                    state=State.OK,
                    summary="Type: gps170, Usage: primary, State: synchronized (MRS GPS sync)",
                ),
                Result(state=State.OK, summary="Next leap second: not announced"),
                Result(state=State.OK, summary="Satellites (total: 8): 6"),
            ],
        ),
        (
            meinberg_lantime_6,
            "1",
            {"levels_lower": ("fixed", (3, 3))},
            [
                Result(
                    state=State.OK,
                    summary="Type: gps180, Usage: primary, State: synchronized (MRS NTP sync)",
                ),
                Result(state=State.OK, summary="Next leap second: 2016-12-31"),
                # satellites are not checked here
            ],
        ),
    ],
)
def test_check_mbg_lantime_ng_refclock_gps(
    info: StringTable, item: str, params: Mapping[str, object], expected: CheckResult
) -> None:
    result = list(check_lantime_ng_refclock_gps(item, params, info))
    assert result == expected
