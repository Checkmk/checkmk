#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime
from zoneinfo import ZoneInfo

import pytest
import time_machine

from cmk.utils.timeperiod import (
    is_timeperiod_active,
    TimeperiodName,
    TimeperiodSpec,
    TimeperiodSpecs,
    validate_day_time_ranges,
    validate_timeperiod_exceptions,
)


def test_is_timeperiod_active() -> None:
    timeperiods: TimeperiodSpecs = {
        TimeperiodName("time_period_1"): {
            "alias": "Simple time period, matches",
            "exclude": [],
            "wednesday": [("11:00", "12:00")],
        },
        TimeperiodName("time_period_2"): {
            "alias": "Simple time period, doe not match",
            "exclude": [],
            "wednesday": [("12:00", "13:00")],
        },
        TimeperiodName("time_period_3"): {
            "alias": "Multiple exceptional day/time, matches",
            "2024-01-03": [("11:10", "11:15")],
            "2024-01-04": [("11:10", "11:15")],  # type: ignore[typeddict-unknown-key]
            "wednesday": [("11:00", "12:00")],
        },
        TimeperiodName("time_period_4"): {
            "alias": "Single exceptional day/time, matches",
            "2024-01-03": [("11:12", "11:15")],  # type: ignore[typeddict-unknown-key]
            "wednesday": [("11:00", "12:00")],
        },
        TimeperiodName("time_period_5"): {
            "alias": "Exclude via timeperiod, does not match",
            "exclude": [TimeperiodName("time_period_1")],
            "wednesday": [("00:00", "24:00")],
        },
        TimeperiodName("time_period_6"): {
            "alias": "Exclude via timeperiod with own exclude, does not match",
            "exclude": [TimeperiodName("time_period_4")],
            "wednesday": [("00:00", "24:00")],
        },
        TimeperiodName("time_period_7"): {
            "alias": "Exceptional by not matching day/time",
            "2024-01-04": [("11:10", "11:15")],  # type: ignore[typeddict-unknown-key]
        },
    }

    # 2024-01-03 11:11
    test_timestamp = 1704276660.0
    with time_machine.travel(datetime.datetime(2024, 1, 1, tzinfo=ZoneInfo("CET"))):
        assert is_timeperiod_active(test_timestamp, TimeperiodName("time_period_1"), timeperiods)
        assert not is_timeperiod_active(
            test_timestamp, TimeperiodName("time_period_2"), timeperiods
        )
        assert is_timeperiod_active(test_timestamp, TimeperiodName("time_period_3"), timeperiods)
        assert is_timeperiod_active(test_timestamp, TimeperiodName("time_period_4"), timeperiods)
        assert not is_timeperiod_active(
            test_timestamp, TimeperiodName("time_period_5"), timeperiods
        )
        assert not is_timeperiod_active(
            test_timestamp, TimeperiodName("time_period_6"), timeperiods
        )
        assert not is_timeperiod_active(
            test_timestamp, TimeperiodName("time_period_7"), timeperiods
        )


@pytest.mark.parametrize(
    "time_period",
    [
        {
            "alias": "Valid time period",
            "exclude": [],
            "monday": [("00:00", "24:00")],
        },
        {
            "alias": "Valid time period with dates",
            "exclude": [],
            "2025-01-01": [("00:00", "24:00")],
        },
        {
            "alias": "Empty time period",
            "exclude": [],
        },
    ],
)
def test_valid_time_periods(time_period: TimeperiodSpec) -> None:
    validate_timeperiod_exceptions(time_period)
    validate_day_time_ranges(time_period)


@pytest.mark.parametrize(
    "time_period, expected_match",
    [
        [
            {
                "alias": "Invalid time period with wrong order",
                "exclude": [],
                "monday": [("24:00", "23:00")],
            },
            "Invalid time range",
        ],
        [
            {
                "alias": "Invalid time period with wrong time",
                "exclude": [],
                "monday": [("0", "24")],
            },
            "Invalid time",
        ],
        [
            {
                "alias": "Invalid time period with typo",
                "exclude": [],
                "moonday": [("12:00", "23:00")],
            },
            "Invalid time period field",
        ],
        [
            {
                "alias": "Invalid time period with wrong date format",
                "exclude": [],
                "01/01/2000": [("12:00", "23:00")],
            },
            "Invalid time period field",
        ],
    ],
)
def test_invalid_time_periods(time_period: TimeperiodSpec, expected_match: str) -> None:
    with pytest.raises(ValueError, match=expected_match):
        validate_day_time_ranges(time_period)
        validate_timeperiod_exceptions(time_period)
