#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from tests.testlib import on_time

from cmk.base.plugins.agent_based import timesyncd
from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, Service, State
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import (
    CheckResult,
    DiscoveryResult,
    StringTable,
)

STRING_TABLE_STANDARD = [
    ["Server:", "91.189.91.157", "(ntp.ubuntu.com)"],
    ["Poll", "interval:", "32s", "(min:", "32s;", "max", "34min", "8s)"],
    ["Leap:", "normal"],
    ["Version:", "4"],
    ["Stratum:", "2"],
    ["Reference:", "C0248F97"],
    ["Precision:", "1us", "(-24)"],
    ["Root", "distance:", "87.096ms", "(max:", "5s)"],
    ["Offset:", "-53.991ms"],
    ["Delay:", "208.839ms"],
    ["Jitter:", "0"],
    ["Packet", "count:", "1"],
    ["Frequency:", "-500,000ppm"],
    ["[[[1569922392.37]]]"],
]
STRING_TABLE_LARGE_OFFSET = [
    ["Server:", "91.189.91.157", "(ntp.ubuntu.com)"],
    ["Poll", "interval:", "32s", "(min:", "32s;", "max", "34min", "8s)"],
    ["Leap:", "normal"],
    ["Version:", "4"],
    ["Stratum:", "2"],
    ["Reference:", "C0248F97"],
    ["Precision:", "1us", "(-24)"],
    ["Root", "distance:", "87.096ms", "(max:", "5s)"],
    [
        "Offset:",
        "-2y",
        "5M",
        "2w",
        "8d",
        "9h",
        "1min",
        "53.991us",
    ],
    ["Delay:", "208.839ms"],
    ["Jitter:", "0"],
    ["Packet", "count:", "1"],
    ["Frequency:", "-500,000ppm"],
    ["[[[1569922392.37]]]"],
]

STRING_TABLE_NO_SYNC = [
    ["Server:", "(null)", "(ntp.ubuntu.com)"],
    ["Poll", "interval:", "0", "(min:", "32s;", "max", "34min", "8s)"],
    ["Packet", "count:", "0"],
    ["[[[1569922392.37]]]"],
]


@pytest.mark.parametrize(
    "string_table, result",
    [
        (STRING_TABLE_STANDARD, [Service()]),
        (STRING_TABLE_LARGE_OFFSET, [Service()]),
        (STRING_TABLE_NO_SYNC, [Service()]),
        ([], []),
    ],
)
def test_discover_timesyncd(  # type:ignore[no-untyped-def]
    string_table: StringTable,
    result: DiscoveryResult,
):
    section = timesyncd.parse_timesyncd(string_table)
    assert list(timesyncd.discover_timesyncd(section)) == result


@pytest.mark.parametrize(
    "string_table, params, result",
    [
        (
            STRING_TABLE_STANDARD,
            timesyncd.default_check_parameters,
            [
                Result(state=State.OK, summary="Offset: 54 milliseconds"),
                Metric("time_offset", 0.053991, levels=(0.2, 0.5)),
                Result(
                    state=State.OK,
                    summary="Time since last sync: 22 hours 1 minute",
                ),
                Metric("last_sync_time", 79260.0),
                Result(state=State.OK, summary="Stratum: 2.00"),
                Result(state=State.OK, summary="Jitter: 0 seconds"),
                Metric("jitter", 0.0, levels=(0.2, 0.5)),
                Result(state=State.OK, summary="Synchronized on 91.189.91.157"),
            ],
        ),
        (
            STRING_TABLE_LARGE_OFFSET,
            timesyncd.default_check_parameters,
            [
                Result(
                    state=State.CRIT,
                    summary="Offset: 2 years 175 days (warn/crit at 200 milliseconds/500 milliseconds)",
                ),
                Metric("time_offset", 78198540.000053991, levels=(0.2, 0.5)),
                Result(
                    state=State.OK,
                    summary="Time since last sync: 22 hours 1 minute",
                ),
                Metric("last_sync_time", 79260.0),
                Result(state=State.OK, summary="Stratum: 2.00"),
                Result(state=State.OK, summary="Jitter: 0 seconds"),
                Metric("jitter", 0.0, levels=(0.2, 0.5)),
                Result(state=State.OK, summary="Synchronized on 91.189.91.157"),
            ],
        ),
        (
            STRING_TABLE_NO_SYNC,
            timesyncd.default_check_parameters,
            [
                Result(
                    state=State.OK,
                    summary="Time since last sync: 22 hours 1 minute",
                ),
                Metric("last_sync_time", 79260.0),
                Result(state=State.OK, summary="Found no time server"),
            ],
        ),
    ],
)
def test_check_timesyncd_freeze(  # type:ignore[no-untyped-def]
    string_table: StringTable,
    params: timesyncd.CheckParams,
    result: CheckResult,
):
    server_time = 1569922392.37 + 60 * 60 * 22 + 60, "UTC"
    section = timesyncd.parse_timesyncd(string_table)
    with on_time(*server_time):
        assert list(timesyncd.check_timesyncd(params, section)) == result


@pytest.mark.parametrize(
    "string_table, params, result",
    [
        (
            STRING_TABLE_NO_SYNC,
            timesyncd.default_check_parameters,
            [
                Result(
                    state=State.CRIT,
                    summary="Cannot reasonably calculate time since last synchronization (hosts time is running ahead)",
                ),
                Result(state=State.OK, summary="Found no time server"),
            ],
        ),
    ],
)
def test_check_timesyncd_negative_time(  # type:ignore[no-untyped-def]
    string_table: StringTable,
    params: timesyncd.CheckParams,
    result: CheckResult,
):
    wrong_server_time = 1569922392.37 - 60, "UTC"
    section = timesyncd.parse_timesyncd(string_table)
    with on_time(*wrong_server_time):
        assert list(timesyncd.check_timesyncd(params, section)) == result
