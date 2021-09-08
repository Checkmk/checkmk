#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Optional

import pytest

from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, State, type_defs
from cmk.base.plugins.agent_based.utils.ups import (
    Battery,
    CHECK_DEFAULT_PARAMETERS,
    check_ups_battery_state,
    check_ups_capacity,
    UpsParameters,
)

SECTION_BATTERY_CAPACITY_DEFAULT = Battery(
    seconds_left=600,
    percent_charged=80,
)

SECTION_ON_BATTERY_YES = Battery(
    on_battery=True,
)

SECTION_ON_BATTERY_NO = Battery(
    on_battery=False,
)

SECTION_SECONDS_ON_BATTERY_DEFAULT = Battery(
    seconds_on_bat=100,
)

RESULTS_ON_BATTERY_WITH_TIME: type_defs.CheckResult = [
    Result(state=State.OK, summary="10 minutes 0 seconds"),
    Metric("battery_seconds_remaining", 600.0),
    Result(state=State.CRIT, summary="80.00% (warn/crit below 95.00%/90.00%)"),
    Metric("battery_capacity", 80.0),
    Result(state=State.OK, summary="Time running on battery: 1 minute 40 seconds"),
]

RESULTS_ON_BATTERY_NO_TIME: type_defs.CheckResult = [
    Result(state=State.OK, summary="10 minutes 0 seconds"),
    Metric("battery_seconds_remaining", 600.0),
    Result(state=State.CRIT, summary="80.00% (warn/crit below 95.00%/90.00%)"),
    Metric("battery_capacity", 80.0),
]

RESULTS_TIME_ON_BATTERY_NO_FLAG: type_defs.CheckResult = [
    Result(
        state=State.WARN,
        summary="10 minutes 0 seconds (warn/crit below 12 minutes 0 seconds/5 minutes 0 seconds)",
    ),
    Metric("battery_seconds_remaining", 600.0),
    Result(state=State.OK, summary="80.00%"),
    Metric("battery_capacity", 80.0),
    Result(state=State.OK, summary="Time running on battery: 1 minute 40 seconds"),
]

RESULTS_NOT_ON_BATTERY: type_defs.CheckResult = [
    Result(state=State.OK, summary="10 minutes 0 seconds"),
    Metric("battery_seconds_remaining", 600.0),
    Result(state=State.OK, summary="On mains"),
    Result(state=State.OK, summary="80.00%"),
    Metric("battery_capacity", 80.0),
]


@pytest.mark.parametrize(
    [
        "params",
        "section_ups_battery_capacity",
        "section_ups_on_battery",
        "section_ups_seconds_on_battery",
        "results",
    ],
    [
        (
            CHECK_DEFAULT_PARAMETERS,
            SECTION_BATTERY_CAPACITY_DEFAULT,
            SECTION_ON_BATTERY_YES,
            SECTION_SECONDS_ON_BATTERY_DEFAULT,
            RESULTS_ON_BATTERY_WITH_TIME,
        ),
        (
            CHECK_DEFAULT_PARAMETERS,
            SECTION_BATTERY_CAPACITY_DEFAULT,
            SECTION_ON_BATTERY_YES,
            None,
            RESULTS_ON_BATTERY_NO_TIME,
        ),
        (
            {
                "battime": (12, 5),
                "capacity": (20, 10),
            },
            SECTION_BATTERY_CAPACITY_DEFAULT,
            None,
            SECTION_SECONDS_ON_BATTERY_DEFAULT,
            RESULTS_TIME_ON_BATTERY_NO_FLAG,
        ),
        (
            CHECK_DEFAULT_PARAMETERS,
            SECTION_BATTERY_CAPACITY_DEFAULT,
            SECTION_ON_BATTERY_NO,
            None,
            RESULTS_NOT_ON_BATTERY,
        ),
    ],
    ids=["on_battery", "on_battery_no_time", "on_battery_no_flag", "not_on_battery"],
)
def test_check_ups_capacity(
    params: UpsParameters,
    section_ups_battery_capacity: Optional[Battery],
    section_ups_on_battery: Optional[Battery],
    section_ups_seconds_on_battery: Optional[Battery],
    results: type_defs.CheckResult,
) -> None:
    assert (
        list(
            check_ups_capacity(
                params,
                section_ups_battery_capacity,
                section_ups_on_battery,
                section_ups_seconds_on_battery,
            )
        )
        == results
    )


SECTION_BATTERY_WARNINGS = Battery(
    fault=False,
    replace=False,
    low=False,
    not_charging=True,
    low_condition=False,
    on_bypass=False,
    backup=False,
    overload=True,
)

SECTION_BATTERY_WARNINGS_OK = Battery(
    fault=False,
    replace=False,
    low=False,
    not_charging=False,
    low_condition=False,
    on_bypass=False,
    backup=False,
    overload=False,
)


@pytest.mark.parametrize(
    [
        "section_ups_battery_warnings",
        "section_ups_on_battery",
        "section_ups_seconds_on_battery",
        "results",
    ],
    [
        (
            SECTION_BATTERY_WARNINGS,
            SECTION_ON_BATTERY_YES,
            None,
            [
                Result(state=State.CRIT, summary="UPS is on battery"),
                Result(state=State.CRIT, summary="Battery is not charging"),
                Result(state=State.CRIT, summary="Overload"),
            ],
        ),
        (
            SECTION_BATTERY_WARNINGS_OK,
            SECTION_ON_BATTERY_NO,
            None,
            [
                Result(state=State.OK, summary="No battery warnings reported"),
            ],
        ),
    ],
    ids=["some_not_ok", "all_ok"],
)
def test_check_ups_battery_state(
    section_ups_battery_warnings: Optional[Battery],
    section_ups_on_battery: Optional[Battery],
    section_ups_seconds_on_battery: Optional[Battery],
    results: type_defs.CheckResult,
) -> None:
    assert (
        list(
            check_ups_battery_state(
                section_ups_battery_warnings,
                section_ups_on_battery,
                section_ups_seconds_on_battery,
            )
        )
        == results
    )
