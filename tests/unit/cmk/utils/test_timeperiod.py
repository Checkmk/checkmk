#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime
from zoneinfo import ZoneInfo

import time_machine

from cmk.utils.timeperiod import is_timeperiod_active, TimeperiodSpecs


def test_is_timeperiod_active() -> None:
    timeperiods: TimeperiodSpecs = {
        "time_period_1": {
            "alias": "Simple time period",  # within time period
            "exclude": [],
            "wednesday": [("11:00", "12:00")],
        },
        "time_period_2": {
            "alias": "Simple time period (False)",  # out of time period
            "exclude": [],
            "wednesday": [("12:00", "13:00")],
        },
        "time_period_3": {
            "alias": "Exclude via exception that matches",  # exclude matches
            "2024-01-03": [("11:10", "11:15")],
            "wednesday": [("11:00", "12:00")],
        },
        "time_period_4": {
            "alias": "Exclude via exception that does not match",  # exclude not matching
            "2024-01-03": [("11:12", "11:15")],
            "wednesday": [("11:00", "12:00")],
        },
        "time_period_5": {
            "alias": "Exclude via timeperiod without own exclude",  # exclude of other timeperiod matches
            "exclude": ["time_period_1"],
            "wednesday": [("00:00", "24:00")],
        },
        "time_period_6": {
            "alias": "Exclude via timeperiod with own exclude",  # exclude of other timeperiod matches
            "exclude": ["time_period_4"],
            "wednesday": [("00:00", "24:00")],
        },
    }

    test_timestamp = 1704276660.0
    with time_machine.travel(datetime.datetime(2024, 1, 1, tzinfo=ZoneInfo("CET"))):
        assert is_timeperiod_active(test_timestamp, "time_period_1", timeperiods)
        assert not is_timeperiod_active(test_timestamp, "time_period_2", timeperiods)
        assert not is_timeperiod_active(test_timestamp, "time_period_3", timeperiods)
        assert is_timeperiod_active(test_timestamp, "time_period_4", timeperiods)
        assert not is_timeperiod_active(test_timestamp, "time_period_5", timeperiods)
        assert not is_timeperiod_active(test_timestamp, "time_period_6", timeperiods)
