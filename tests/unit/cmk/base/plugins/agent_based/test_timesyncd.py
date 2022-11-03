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

# server cannot be reached
STRING_TABLE_NO_SERVER = [
    ["Server:", "(null)", "(ntp.ubuntu.com)"],
    ["Poll", "interval:", "0", "(min:", "32s;", "max", "34min", "8s)"],
    ["Packet", "count:", "0"],
    ["[[[1569922392.37]]]"],
]

# server is configured and can be resolved, but e.g. NTP blocked by firewall
STRING_TABLE_SERVER_NO_SYNC = [
    ["Server:", "10.200.0.1", "10.200.0.1"],
    ["Poll", "interval:", "34min 8s", "(min:", "32s;", "max", "34min", "8s)"],
    ["Packet", "count:", "0"],
    ["[[[1569922392.37]]]"],
]

STRING_TABLE_SERVER_NTP_MESSAGE = [
    [
        "NTPMessage={ Leap=0, Version=4, Mode=4, Stratum=2, Precision=-24, RootDelay=87.096ms, RootDispersion=26.397ms, Reference=C0248F97, OriginateTimestamp=Tue 2019-10-01 11:33:12 CEST, ReceiveTimestamp=Tue 2019-10-01 11:33:12 CEST, TransmitTimestamp=Tue 2019-10-01 11:33:12 CEST, DestinationTimestamp=Tue 2019-10-01 11:33:12 CEST, Ignored=no PacketCount=1, Jitter=0ms }"
    ],
    ["Timezone=Europe/Berlin"],
]

STRING_TABLE_NO_SYNC_NTP_MESSAGE = [
    ["Timezone=Europe/Berlin"],
]


@pytest.mark.parametrize(
    "string_table, string_table_ntpmessage,  result",
    [
        (STRING_TABLE_STANDARD, [], [Service()]),
        (STRING_TABLE_LARGE_OFFSET, [], [Service()]),
        (STRING_TABLE_NO_SERVER, STRING_TABLE_NO_SYNC_NTP_MESSAGE, [Service()]),
        (STRING_TABLE_SERVER_NO_SYNC, STRING_TABLE_NO_SYNC_NTP_MESSAGE, [Service()]),
        (STRING_TABLE_STANDARD, STRING_TABLE_SERVER_NTP_MESSAGE, [Service()]),
        ([], [], []),
    ],
)
def test_discover_timesyncd(
    string_table: StringTable,
    string_table_ntpmessage: StringTable,
    result: DiscoveryResult,
):
    section = timesyncd.parse_timesyncd(string_table)
    section_ntpmessage = timesyncd.parse_timesyncd_ntpmessage(string_table_ntpmessage)
    assert list(timesyncd.discover_timesyncd(section, section_ntpmessage)) == result


@pytest.mark.parametrize(
    "string_table, string_table_ntpmessage, params, result",
    [
        (
            STRING_TABLE_STANDARD,
            [],
            timesyncd.default_check_parameters,
            [
                Result(state=state.OK, summary="Offset: 54 milliseconds"),
                Metric("time_offset", 0.053991, levels=(0.2, 0.5)),
                Result(
                    state=state.OK,
                    summary="Time since last sync: 22 hours 1 minute",
                ),
                Metric("last_sync_time", 79260.0),
                Result(state=state.OK, summary="Stratum: 2.00"),
                Result(state=state.OK, summary="Jitter: 0 seconds"),
                Metric("jitter", 0.0, levels=(0.2, 0.5)),
                Result(state=state.OK, summary="Synchronized on 91.189.91.157"),
            ],
        ),
        (
            STRING_TABLE_LARGE_OFFSET,
            [],
            timesyncd.default_check_parameters,
            [
                Result(
                    state=state.CRIT,
                    summary="Offset: 2 years 175 days (warn/crit at 200 milliseconds/500 milliseconds)",
                ),
                Metric("time_offset", 78198540.000053991, levels=(0.2, 0.5)),
                Result(
                    state=state.OK,
                    summary="Time since last sync: 22 hours 1 minute",
                ),
                Metric("last_sync_time", 79260.0),
                Result(state=state.OK, summary="Stratum: 2.00"),
                Result(state=state.OK, summary="Jitter: 0 seconds"),
                Metric("jitter", 0.0, levels=(0.2, 0.5)),
                Result(state=state.OK, summary="Synchronized on 91.189.91.157"),
            ],
        ),
        (
            STRING_TABLE_NO_SERVER,
            [],
            timesyncd.default_check_parameters,
            [
                Result(
                    state=state.OK,
                    summary="Time since last sync: 22 hours 1 minute",
                ),
                Metric("last_sync_time", 79260.0),
                Result(state=state.CRIT, summary="Found no time server"),
            ],
        ),
        (
            STRING_TABLE_SERVER_NO_SYNC,
            [],
            timesyncd.default_check_parameters,
            [
                Result(
                    state=state.OK,
                    summary="Time since last sync: 22 hours 1 minute",
                ),
                Metric("last_sync_time", 79260.0),
                Result(state=state.CRIT, summary="Found no time server"),
            ],
        ),
        (
            STRING_TABLE_STANDARD,
            STRING_TABLE_SERVER_NTP_MESSAGE,
            timesyncd.default_check_parameters,
            [
                Result(state=state.OK, summary="Offset: 54 milliseconds"),
                Metric("time_offset", 0.053991, levels=(0.2, 0.5)),
                Result(
                    state=state.OK,
                    summary="Time since last sync: 22 hours 1 minute",
                ),
                Metric("last_sync_time", 79260.0),
                Result(
                    state=state.CRIT,
                    summary="Time since last NTPMessage: 22 hours 1 minute (warn/crit at 1 hour 0 minutes/2 hours 0 minutes)",
                ),
                Metric("last_sync_receive_time", 79260.36999988556, levels=(3600.0, 7200.0)),
                Result(state=state.OK, summary="Stratum: 2.00"),
                Result(state=state.OK, summary="Jitter: 0 seconds"),
                Metric("jitter", 0.0, levels=(0.2, 0.5)),
                Result(state=state.OK, summary="Synchronized on 91.189.91.157"),
            ],
        ),
    ],
)
def test_check_timesyncd_freeze(
    string_table: StringTable,
    string_table_ntpmessage: StringTable,
    params: timesyncd.CheckParams,
    result: CheckResult,
):
    server_time = 1569922392.37 + 60 * 60 * 22 + 60, "UTC"
    section = timesyncd.parse_timesyncd(string_table)
    section_ntpmessage = timesyncd.parse_timesyncd_ntpmessage(string_table_ntpmessage)
    with on_time(*server_time):
        assert list(timesyncd.check_timesyncd(params, section, section_ntpmessage)) == result


@pytest.mark.parametrize(
    "string_table, string_table_ntpmessage, params, result",
    [
        (
            STRING_TABLE_NO_SERVER,
            [],
            timesyncd.default_check_parameters,
            [
                Result(
                    state=state.CRIT,
                    summary="Cannot reasonably calculate time since last synchronization (hosts time is running ahead)",
                ),
                Result(state=state.CRIT, summary="Found no time server"),
            ],
        ),
    ],
)
def test_check_timesyncd_negative_time(
    string_table: StringTable,
    string_table_ntpmessage: StringTable,
    params: timesyncd.CheckParams,
    result: CheckResult,
):
    wrong_server_time = 1569922392.37 - 60, "UTC"
    section = timesyncd.parse_timesyncd(string_table)
    section_ntpmessage = timesyncd.parse_timesyncd_ntpmessage(string_table_ntpmessage)
    with on_time(*wrong_server_time):
        assert list(timesyncd.check_timesyncd(params, section, section_ntpmessage)) == result
