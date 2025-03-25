#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime
from zoneinfo import ZoneInfo

import time_machine

from cmk.agent_based.v2 import Metric, Result, State
from cmk.plugins.collection.agent_based import chrony


def test_chrony_parse_errmsg() -> None:
    assert chrony.parse_chrony([["506", "Cannot", "talk", "to", "daemon"]]) == {
        "error": "506 Cannot talk to daemon",
    }


def test_chrony_parse_valid() -> None:
    with time_machine.travel(datetime.datetime.fromtimestamp(1628000000, tz=ZoneInfo("UTC"))):
        assert chrony.parse_chrony(
            [
                ["Reference", "ID", ":", "55DCBEF6", "(kaesekuchen.ok)"],
                ["Stratum", ":", "3"],
                ["Ref", "time", "(UTC)", ":", "Tue", "Jul", "09", "08:01:06", "2019"],
                ["System", "time", ":", "0.000275117", "seconds", "slow", "of", "NTP", "time"],
                ["Last", "offset", ":", "-0.000442775", "seconds"],
                ["RMS", "offset", ":", "0.000999328", "seconds"],
                ["Frequency", ":", "2.054", "ppm", "fast"],
                ["Residual", "freq", ":", "-0.004", "ppm"],
                ["Skew", ":", "0.182", "ppm"],
                ["Root", "delay", ":", "0.023675382", "seconds"],
                ["Root", "dispersion", ":", "0.001886752", "seconds"],
                ["Update", "interval", ":", "1042.2", "seconds"],
                ["Leap", "status", ":", "Normal"],
            ]
        ) == {
            "Reference ID": "55DCBEF6 (kaesekuchen.ok)",
            "Stratum": 3,
            "System time": 0.275117,
            "address": "(kaesekuchen.ok)",
            "last_sync": 65340734.0,
        }


def test_chrony_discover_skip_on_error_with_ntp() -> None:
    assert not list(chrony.discover_chrony({"error": "some error"}, "something trueish"))


def test_chrony_discover_error_without_ntp() -> None:
    assert list(chrony.discover_chrony({"error": "some error"}, []))


def test_chrony_servers_unreachable() -> None:
    assert list(
        chrony.check_chrony(
            {"ntp_levels": (None, None, None)},
            {
                "Reference ID": "55DCBEF6 ()",
                "address": None,
            },
            None,
        )
    ) == [
        Result(
            state=State.WARN,
            notice="NTP servers: unreachable\nReference ID: 55DCBEF6 ()",
        )
    ]


def test_chrony_stratum_crit() -> None:
    assert list(
        chrony.check_chrony(
            {"ntp_levels": (2, None, None)},
            {
                "Reference ID": None,
                "Stratum": 3,
                "System time": None,
                "address": "(foo.bar)",
            },
            None,
        )
    ) == [
        Result(state=State.OK, notice="NTP servers: (foo.bar)\nReference ID: None"),
        Result(
            state=State.CRIT,
            summary="Stratum: 3 (warn/crit at 2/2)",
        ),
    ]


def test_chrony_offet_crit() -> None:
    assert list(
        chrony.check_chrony(
            {"ntp_levels": (None, 0.12, 0.42)},
            {
                "Reference ID": None,
                "Stratum": None,
                "System time": 0.275117,
                "address": "(moo)",
            },
            None,
        )
    ) == [
        Result(state=State.OK, notice="NTP servers: (moo)\nReference ID: None"),
        Result(
            state=State.WARN,
            summary="Offset: 0.2751 ms (warn/crit at 0.1200 ms/0.4200 ms)",
        ),
        Metric("offset", 0.275117, levels=(0.12, 0.42), boundaries=(0.0, None)),
    ]


def test_chrony_last_sync() -> None:
    assert list(
        chrony.check_chrony(
            {"ntp_levels": (None, 0.12, 0.42), "alert_delay": (1800, 3600)},
            {
                "last_sync": 1860,
                "address": "(moo)",
            },
            None,
        )
    ) == [
        Result(state=State.OK, notice="NTP servers: (moo)\nReference ID: None"),
        Result(
            state=State.WARN,
            summary="Time since last sync: 31 minutes 0 seconds (warn/crit at 30 minutes 0 seconds/1 hour 0 minutes)",
        ),
    ]


def test_chrony_negative_sync_time() -> None:
    assert list(
        chrony.check_chrony(
            {"ntp_levels": (None, 0.12, 0.42), "alert_delay": (1800, 3600)},
            {
                "last_sync": -200,
                "address": "(moo)",
            },
            None,
        )
    ) == [
        Result(state=State.OK, notice="NTP servers: (moo)\nReference ID: None"),
        Result(
            state=State.OK,
            summary="Last synchronization appears to be 3 minutes 20 seconds in the future (check your system time)",
        ),
    ]


def test_chrony_section_is_none() -> None:
    assert not list(
        chrony.check_chrony(
            {
                "ntp_levels": (10, 200.0, 500.0),
                "alert_delay": (1800, 3600),
            },
            None,
            None,
        )
    )
