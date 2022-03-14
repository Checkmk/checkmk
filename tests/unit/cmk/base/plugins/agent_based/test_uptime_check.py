#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from tests.testlib import on_time

from cmk.base.plugins.agent_based import uptime
from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, State
from cmk.base.plugins.agent_based.utils import uptime as uptime_utils

# Mark all tests in this file as check related tests
pytestmark = pytest.mark.checks


@pytest.mark.parametrize(
    "string, result",
    [
        ("22 day(s),  8:46", 1932360),
        ("4 day(s),  3 hr(s)", 356400),
        ("76 day(s), 26 min(s)", 6567960),
        ("1086 day(s)", 93830400),
        ("5 min(s)", 300),
        ("2 hr(s)", 7200),
    ],
)
def test_human_read_uptime(string, result):
    assert uptime.parse_human_read_uptime(string) == result


@pytest.mark.parametrize(
    "section, do_discover",
    [
        (uptime_utils.Section(12, None), True),
        (uptime_utils.Section(None, None), False),
    ],
)
def test_uptime_discovery(section, do_discover):
    assert bool(list(uptime_utils.discover(section))) is do_discover


def test_uptime_check_basic():

    with on_time("2018-04-15 16:50", "CET"):
        assert list(uptime_utils.check({}, uptime_utils.Section(123, None))) == [
            Result(state=State.OK, summary="Up since Apr 15 2018 18:47:57"),
            Result(state=State.OK, summary="Uptime: 2 minutes 3 seconds"),
            Metric("uptime", 123.0),
        ]


def test_uptime_check_zero():
    with on_time("2018-04-15 16:50", "CET"):
        assert list(uptime_utils.check({}, uptime_utils.Section(0, None))) == [
            Result(state=State.OK, summary="Up since Apr 15 2018 18:50:00"),
            Result(state=State.OK, summary="Uptime: 0 seconds"),
            Metric("uptime", 0.0),
        ]


@pytest.mark.parametrize(
    "info, reference",
    [
        (
            [
                ["22731"],
                ["[uptime_solaris_start]"],
                ["SunOS", "unknown", "5.10", "Generic_147148-26", "i86pc", "i386", "i86pc"],
                ["global"],
                [
                    "4:58pm",
                    "up",
                    "6:19,",
                    "2",
                    "users,",
                    "load",
                    "average:",
                    "0.18,",
                    "0.06,",
                    "0.03",
                ],
                ["unix:0:system_misc:snaptime", "22737.886916295"],
                ["[uptime_solaris_end]"],
            ],
            [
                Result(state=State.OK, summary="Up since Apr 15 2018 12:31:09"),
                Result(state=State.OK, summary="Uptime: 6 hours 18 minutes"),
                Metric("uptime", 22731),
            ],
        ),
        (
            [
                ["1122"],
                ["[uptime_solaris_start]"],
                ["SunOS", "unknown", "5.10", "Generic_147148-26", "i86pc", "i386", "i86pc"],
                ["global"],
                [
                    "4:23pm",
                    "up",
                    "19",
                    "min(s),",
                    "2",
                    "users,",
                    "load",
                    "average:",
                    "0.03,",
                    "0.09,",
                    "0.09",
                ],
                ["unix:0:system_misc:snaptime", "1131.467157594"],
                ["[uptime_solaris_end]"],
            ],
            [
                Result(state=State.OK, summary="Up since Apr 15 2018 18:31:18"),
                Result(state=State.OK, summary="Uptime: 18 minutes 42 seconds"),
                Metric("uptime", 1122),
            ],
        ),
        (
            [
                ["1553086171"],
                ["[uptime_solaris_start]"],
                ["SunOS", "Solaris", "11.3", "X86"],
                ["non-global", "zone"],
                [
                    "1:53pm",
                    "up",
                    "335",
                    "day(s),",
                    "23:13,",
                    "0",
                    "users,",
                    "load",
                    "average:",
                    "0.36,",
                    "0.34,",
                    "0.34",
                ],
                ["unix:0:system_misc:snaptime", "29027808.0471184"],
                ["[uptime_solaris_end]"],
            ],
            [
                Result(state=State.OK, summary="Up since May 14 2017 19:33:11"),
                Result(state=State.OK, summary="Uptime: 335 days 23 hours"),
                Metric("uptime", 29027808.0471184),
            ],
        ),
        (
            [
                ["54043590"],
                ["[uptime_solaris_start]"],
                ["SunOS", "sveqdcmk01", "5.10", "Generic_150401-49", "i86pc", "i386", "i86pc"],
                ["sveqdcmk01"],
                [
                    "1:50pm",
                    "up",
                    "420",
                    "day(s),",
                    "21:05,",
                    "43",
                    "users,",
                    "load",
                    "average:",
                    "16.75,",
                    "19.66,",
                    "18.18",
                ],
                ["unix:0:system_misc:snaptime", "54048049.7479652"],
                ["[uptime_solaris_end]"],
            ],
            [
                Result(
                    state=State.UNKNOWN,
                    summary=(
                        "Your Solaris system gives inconsistent uptime information. Please get it fixed. "
                        "Uptime command: 420 days, 21:05:00; Kernel time since boot: 625 days, 12:06:30; "
                        "Snaptime: 625 days, 13:20:49.747965"
                    ),
                ),
            ],
        ),
        (
            [
                ["1529194584"],
                ["[uptime_solaris_start]"],
                ["SunOS", "sc000338", "5.10", "Generic_150400-61", "sun4v", "sparc", "SUNW"],
                ["sc000338"],
                [
                    "1:50pm",
                    "up",
                    "282",
                    "day(s),",
                    "13:40,",
                    "1",
                    "user,",
                    "load",
                    "average:",
                    "3.38,",
                    "3.44,",
                    "3.49",
                ],
                ["unix:0:system_misc:snaptime", "70236854.9797181"],
                ["[uptime_solaris_end]"],
            ],
            [
                Result(
                    state=State.UNKNOWN,
                    summary=(
                        "Your Solaris system gives inconsistent uptime information. Please get it fixed. "
                        "Uptime command: 282 days, 13:40:00; Kernel time since boot: 17699 days, 0:16:24; "
                        "Snaptime: 812 days, 22:14:14.979718"
                    ),
                ),
            ],
        ),
    ],
)
def test_uptime_solaris_inputs(info, reference):

    section = uptime.parse_uptime(info)
    assert section is not None

    # This time freeze has no correlation with the uptime of the test. It
    # is needed for the check output to always return the same infotext.
    # The true test happens on state and perfdata
    with on_time("2018-04-15 16:50", "CET"):
        result = list(uptime_utils.check({}, section))

    assert result == reference
