#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime
from collections.abc import Mapping, Sequence
from typing import Any
from zoneinfo import ZoneInfo

import pytest
import time_machine

from cmk.agent_based.v2 import Metric, Result, State, StringTable
from cmk.plugins.collection.agent_based import uptime
from cmk.plugins.lib import uptime as uptime_utils

# Mark all tests in this file as check related tests


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
def test_human_read_uptime(string: str, result: float) -> None:
    assert uptime.parse_human_read_uptime(string) == result


@pytest.mark.parametrize(
    "section, do_discover",
    [
        (uptime_utils.Section(12, None), True),
        (uptime_utils.Section(None, None), False),
    ],
)
def test_uptime_discovery(section: uptime_utils.Section, do_discover: bool) -> None:
    assert bool(list(uptime_utils.discover(section))) is do_discover


def test_uptime_check_basic() -> None:
    with time_machine.travel(datetime.datetime(2018, 4, 15, 16, 50, 0, tzinfo=ZoneInfo("CET"))):
        assert list(uptime_utils.check({}, uptime_utils.Section(123, None))) == [
            Result(state=State.OK, summary="Up since 2018-04-15 16:47:57"),
            Result(state=State.OK, summary="Uptime: 2 minutes 3 seconds"),
            Metric("uptime", 123.0),
        ]


def test_uptime_check_zero() -> None:
    with time_machine.travel(datetime.datetime(2018, 4, 15, 16, 50, 0, tzinfo=ZoneInfo("CET"))):
        assert list(uptime_utils.check({}, uptime_utils.Section(0, None))) == [
            Result(state=State.OK, summary="Up since 2018-04-15 16:50:00"),
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
                Result(state=State.OK, summary="Up since 2018-04-15 10:31:09"),
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
                Result(state=State.OK, summary="Up since 2018-04-15 16:31:18"),
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
                Result(state=State.OK, summary="Up since 2017-05-14 17:33:11"),
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
        (  # SUP-16709
            [
                [
                    "22",
                ],
                [
                    "[uptime_solaris_start]",
                ],
                [
                    "SunOS",
                    "ssssssss",
                    "5.55",
                    "11.1.11.111.1",
                    "sssss",
                    "sssss",
                    "sssss",
                    "nnnnnnnnnnnnnnn",
                ],
                [
                    "ssssssss",
                ],
                [
                    "3:19am",
                    "up<",
                    "1",
                    "minute,",
                    "0",
                    "users,",
                    "load",
                    "average:",
                    "1.79,",
                    "0.44,",
                    "0.15",
                ],
                ["unix:0:system_misc:snaptime", "5931.036430995"],
                [
                    "[uptime_solaris_end]",
                ],
            ],
            [
                Result(state=State.OK, summary="Up since 2018-04-15 16:49:38"),
                Result(state=State.OK, summary="Uptime: 22 seconds"),
                Metric("uptime", 22.0),
            ],
        ),
        (
            [
                [
                    "-45",
                ],
                [
                    "[uptime_solaris_start]",
                ],
                [
                    "SunOS",
                    "ssssssss",
                    "5.55",
                    "11.1.11.111.1",
                    "sssss",
                    "sssss",
                    "sssss",
                    "nnnnnnnnnnnnnnn",
                ],
                [
                    "ssssssss",
                ],
                [
                    "1:57am",
                    "up",
                    "1",
                    "min(s),",
                    "0",
                    "users,",
                    "load",
                    "average:",
                    "2.88,",
                    "1.09,",
                    "0.45",
                ],
                [
                    "unix:0:system_misc:snaptime",
                    "817.282012635",
                ],
                [
                    "[uptime_solaris_end]",
                ],
            ],
            [
                Result(
                    state=State.UNKNOWN,
                    summary="Your Solaris system reported to be booted in the future.",
                )
            ],
        ),
    ],
)
def test_uptime_solaris_inputs(info: StringTable, reference: Sequence[Result]) -> None:
    section = uptime.parse_uptime(info)
    assert section is not None

    # This time freeze has no correlation with the uptime of the test. It
    # is needed for the check output to always return the same infotext.
    # The true test happens on state and perfdata
    with time_machine.travel(datetime.datetime(2018, 4, 15, 16, 50, 0, tzinfo=ZoneInfo("CET"))):
        result = list(uptime_utils.check({}, section))

    assert result == reference


_EXPECTED_NO_LEVELS = [
    Result(state=State.OK, summary="Up since 2018-04-15 10:31:09"),
    Result(state=State.OK, summary="Uptime: 6 hours 18 minutes"),
    Metric("uptime", 22731.0),
]

_EXPECTED_FIXED_LEVELS = [
    Result(state=State.OK, summary="Up since 2018-04-15 10:31:09"),
    Result(
        state=State.CRIT,
        summary="Uptime: 6 hours 18 minutes (warn/crit at 10 seconds/20 seconds)",
    ),
    Metric("uptime", 22731.0, levels=(10.0, 20.0)),
]


@pytest.mark.parametrize(
    "params, expected",
    [
        pytest.param({}, _EXPECTED_NO_LEVELS, id="no_params"),
        pytest.param({"max": ("no_levels", None)}, _EXPECTED_NO_LEVELS, id="api v2 no_levels"),
        pytest.param(
            {"max": (10, 20)},
            _EXPECTED_FIXED_LEVELS,
            id="api v1 fixed",
        ),
        pytest.param(
            {"max": ("fixed", (10, 20))},
            _EXPECTED_FIXED_LEVELS,
            id="api v2 fixed",
        ),
        pytest.param(
            {"max": ("predictive", ("uptime", 10, (10, 20)))},
            [
                Result(state=State.OK, summary="Up since 2018-04-15 10:31:09"),
                Result(
                    state=State.CRIT,
                    summary="Uptime: 6 hours 18 minutes (prediction: 10 seconds) (warn/crit at 10 "
                    "seconds/20 seconds)",
                ),
                Metric("uptime", 22731.0, levels=(10.0, 20.0)),
                Metric("predict_uptime", 10.0),
            ],
            id="api v2 predictive",
        ),
    ],
)
def test_uptime_levels_diff_api_versions(
    params: Mapping[str, Any], expected: list[Result | Metric]
) -> None:
    """Check that the uptime library can handle different API versions for level definitions.
    Can be removed when all the rulesets of the checks using the library are migrated to v2."""
    # This time freeze has no correlation with the uptime of the test. It
    # is needed for the check output to always return the same infotext.
    # The true test happens on state and perfdata
    with time_machine.travel(datetime.datetime(2018, 4, 15, 16, 50, 0, tzinfo=ZoneInfo("CET"))):
        result = list(
            uptime_utils.check(params, uptime_utils.Section(uptime_sec=22731, message=None))
        )

    assert result == expected
