#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from tests.testlib import on_time

from cmk.base.plugins.agent_based import timesyncd
from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, Service
from cmk.base.plugins.agent_based.agent_based_api.v1 import State as state
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import (
    CheckResult,
    DiscoveryResult,
    StringTable,
)

DATA1 = [
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

DATA2 = [
    ["Server:", "(null)", "(ntp.ubuntu.com)"],
    ["Poll", "interval:", "0", "(min:", "32s;", "max", "34min", "8s)"],
    ["Packet", "count:", "0"],
    ["[[[1569922392.37]]]"],
]


@pytest.mark.parametrize(
    "string_table, result",
    [
        (DATA1, [Service()]),
        (DATA2, [Service()]),
        ([], []),
    ],
)
def test_discover_timesyncd(
    string_table: StringTable,
    result: DiscoveryResult,
):
    section = timesyncd.parse_timesyncd(string_table)
    assert list(timesyncd.discover_timesyncd(section)) == result


@pytest.mark.parametrize(
    "string_table, params, result",
    [
        (
            DATA1,
            timesyncd.default_check_parameters,
            [
                Result(state=state.OK, summary="Offset: 54 milliseconds"),
                Metric("time_offset", 0.053991, levels=(0.2, 0.5)),
                Result(
                    state=state.CRIT,
                    summary="Time since last sync: 22 hours 1 minute (warn/crit at 2 hours 5 minutes/3 hours 0 minutes)",
                ),
                Result(state=state.OK, summary="Stratum: 2.00"),
                Result(state=state.OK, summary="Jitter: Jan 01 1970 00:00:00"),
                Metric("jitter", 0.0, levels=(0.2, 0.5)),
                Result(state=state.OK, summary="Synchronized on 91.189.91.157"),
            ],
        ),
        (
            DATA2,
            timesyncd.default_check_parameters,
            [
                Result(
                    state=state.CRIT,
                    summary="Time since last sync: 22 hours 1 minute (warn/crit at 2 hours 5 minutes/3 hours 0 minutes)",
                ),
                Result(state=state.OK, summary="Found no time server"),
            ],
        ),
    ],
)
def test_check_timesyncd_freeze(
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
            DATA2,
            timesyncd.default_check_parameters,
            [
                Result(
                    state=state.CRIT,
                    summary="Cannot reasonably calculate time since last synchronization (hosts time is running ahead)",
                ),
                Result(state=state.OK, summary="Found no time server"),
            ],
        ),
    ],
)
def test_check_timesyncd_negative_time(
    string_table: StringTable,
    params: timesyncd.CheckParams,
    result: CheckResult,
):
    wrong_server_time = 1569922392.37 - 60, "UTC"
    section = timesyncd.parse_timesyncd(string_table)
    with on_time(*wrong_server_time):
        assert list(timesyncd.check_timesyncd(params, section)) == result
