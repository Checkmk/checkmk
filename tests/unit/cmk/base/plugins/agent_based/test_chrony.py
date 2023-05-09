#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, State as state
from cmk.base.plugins.agent_based import chrony

from testlib import on_time


def test_chrony_parse_errmsg():
    assert chrony.parse_chrony([[u'506', u'Cannot', u'talk', u'to', u'daemon']]) == {
        "error": "506 Cannot talk to daemon",
    }


def test_chrony_parse_valid():
    with on_time(1628000000, 'UTC'):
        assert chrony.parse_chrony([
            [u'Reference', u'ID', u':', u'55DCBEF6', u'(kaesekuchen.ok)'],
            [u'Stratum', u':', u'3'],
            [u'Ref', u'time', u'(UTC)', u':', u'Tue', u'Jul', u'09', u'08:01:06', u'2019'],
            [u'System', u'time', u':', u'0.000275117', u'seconds', u'slow', u'of', u'NTP', u'time'],
            [u'Last', u'offset', u':', u'-0.000442775', u'seconds'],
            [u'RMS', u'offset', u':', u'0.000999328', u'seconds'],
            [u'Frequency', u':', u'2.054', u'ppm', u'fast'],
            [u'Residual', u'freq', u':', u'-0.004', u'ppm'],
            [u'Skew', u':', u'0.182', u'ppm'],
            [u'Root', u'delay', u':', u'0.023675382', u'seconds'],
            [u'Root', u'dispersion', u':', u'0.001886752', u'seconds'],
            [u'Update', u'interval', u':', u'1042.2', u'seconds'],
            [u'Leap', u'status', u':', u'Normal'],
        ]) == {
            "Reference ID": '55DCBEF6 (kaesekuchen.ok)',
            "Stratum": 3,
            "System time": 0.275117,
            "address": "(kaesekuchen.ok)",
            'last_sync': 65340734.0,
        }


def test_chrony_discover_skip_on_error_with_ntp():
    assert not list(chrony.discover_chrony({"error": "some error"}, "something trueish"))


def test_chrony_discover_error_without_ntp():
    assert list(chrony.discover_chrony({"error": "some error"}, []))


def test_chrony_servers_unreachable():
    assert list(
        chrony.check_chrony({"ntp_levels": (None, None, None)}, {
            "Reference ID": '55DCBEF6 ()',
            "address": "()",
        }, None)) == [
            Result(
                state=state.WARN,
                notice="NTP servers: unreachable\nReference ID: 55DCBEF6 ()",
            )
        ]


def test_chrony_stratum_crit():
    assert list(
        chrony.check_chrony({"ntp_levels": (2, None, None)}, {
            "Reference ID": None,
            "Stratum": 3,
            "System time": None,
            "address": "(foo.bar)",
        }, None)) == [
            Result(state=state.OK, notice='NTP servers: (foo.bar)\nReference ID: None'),
            Result(
                state=state.CRIT,
                summary="Stratum: 3 (warn/crit at 2/2)",
            ),
        ]


def test_chrony_offet_crit():
    assert list(
        chrony.check_chrony({"ntp_levels": (None, 0.12, 0.42)}, {
            "Reference ID": None,
            "Stratum": None,
            "System time": 0.275117,
            "address": "(moo)",
        }, None)) == [
            Result(state=state.OK, notice='NTP servers: (moo)\nReference ID: None'),
            Result(
                state=state.WARN,
                summary="Offset: 0.2751 ms (warn/crit at 0.1200 ms/0.4200 ms)",
            ),
            Metric("offset", 0.275117, levels=(0.12, 0.42), boundaries=(0.0, None)),
        ]


def test_chrony_last_sync():
    assert list(
        chrony.check_chrony({
            "ntp_levels": (None, 0.12, 0.42),
            'alert_delay': (1800, 3600)
        }, {
            "last_sync": 1860,
            "address": "(moo)",
        }, None)
    ) == [
        Result(state=state.OK, notice='NTP servers: (moo)\nReference ID: None'),
        Result(
            state=state.WARN,
            summary=
            "Time since last sync: 31 minutes 0 seconds (warn/crit at 30 minutes 0 seconds/1 hour 0 minutes)",
        ),
    ]


def test_chrony_section_is_none() -> None:
    assert (list(
        chrony.check_chrony(
            {
                "ntp_levels": (10, 200.0, 500.0),
                "alert_delay": (1800, 3600),
            },
            None,
            None,
        )) == [])
