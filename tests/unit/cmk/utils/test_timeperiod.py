#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime
from zoneinfo import ZoneInfo

import pytest
import recurring_ical_events  # type: ignore[import-untyped,unused-ignore]
import time_machine
from icalendar import Calendar

from cmk.gui.wato.pages.timeperiods import ICalEvent, TimeperiodUsage
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


ICAL_DATA_LIST = list[dict[str, str]]


def create_ical_file(ical_data_list: ICAL_DATA_LIST) -> str:
    ical_string = """
BEGIN:VCALENDAR
PRODID:-//TEST//EN
VERSION:2.0
"""
    for item in ical_data_list:
        ical_string += f"""
BEGIN:VEVENT
DTSTAMP:20240313T032001Z
CREATED:20240313T032001Z
UID:F_2024_TEST_{item["dtstart"]}
DESCRIPTION:{item["description"]}
SUMMARY:{item["summary"]}
DTSTART;{item["dtstart"]}
DTEND;{item["dtend"]}
TRANSP:TRANSPARENT
END:VEVENT
"""

    ical_string += "END:VCALENDAR"
    return ical_string


def test_fetch_recurring_events() -> None:
    ical_data = [
        {
            "dtstart": "VALUE=DATE:20240212",
            "dtend": "VALUE=DATE:20240217",
            "summary": "Test event 1",
            "description": "Test event 1",
        },
        {
            "dtstart": "VALUE=DATE:20240325",
            "dtend": "VALUE=DATE:20240407",
            "summary": "Test event 2",
            "description": "Test event 2",
        },
        {
            "dtstart": "VALUE=DATE:20241028",
            "dtend": "VALUE=DATE:20241101",
            "summary": "Test event 3",
            "description": "Test event 3",
        },
    ]

    with time_machine.travel(datetime.datetime(2024, 4, 15, tzinfo=ZoneInfo("CET"))):
        ical_string = create_ical_file(ical_data)
        cal_obj: Calendar = Calendar.from_ical(ical_string)  # type: ignore[assignment]

    recurring_events = recurring_ical_events.of(cal_obj).between("20240415", "20250101")

    assert len(recurring_events) == 1


def test_convert_full_day_exceptions() -> None:
    data = [
        {
            "dtstart": "VALUE=DATE:20240801",
            "dtend": "VALUE=DATE:20240802",
            "summary": "Single day event",
            "description": "Single day event",
        },
        {
            "dtstart": "VALUE=DATE:20240810",
            "dtend": "VALUE=DATE:20240814",
            "summary": "4 days event",
            "description": "4 days event",
        },
    ]

    with time_machine.travel(datetime.datetime(2024, 4, 15, tzinfo=ZoneInfo("CET"))):
        ical_string = create_ical_file(data)
        cal_obj: Calendar = Calendar.from_ical(ical_string)  # type: ignore[assignment]

    recurring_events = recurring_ical_events.of(cal_obj).between("20240415", "20250101")

    exceptions: dict[str, TimeperiodUsage] = {}

    for e in recurring_events:
        ice = ICalEvent(e)
        exceptions = {**exceptions, **ice.to_timeperiod_exception()}

    available_dates = ["2024-08-01", "2024-08-10", "2024-08-11", "2024-08-12", "2024-08-13"]

    assert len(exceptions) == 5

    for date in available_dates:
        assert date in exceptions
        assert exceptions[date] == (("00:00", "24:00"))


def test_convert_partial_start_day_exceptions() -> None:
    data = [
        {
            "dtstart": "TZID=UTC:20240801T120000Z",
            "dtend": "VALUE=DATE:20240802",
            "summary": "Single day event",
            "description": "Single day event",
        },
        {
            "dtstart": "TZID=UTC:20240810T120000Z",
            "dtend": "VALUE=DATE:20240814",
            "summary": "4 days event",
            "description": "4 days event",
        },
    ]

    with time_machine.travel(datetime.datetime(2024, 4, 15, tzinfo=ZoneInfo("UTC"))):
        ical_string = create_ical_file(data)
        cal_obj: Calendar = Calendar.from_ical(ical_string)  # type: ignore[assignment]

        recurring_events = recurring_ical_events.of(cal_obj).between("20240415", "20250101")

        exceptions: dict[str, TimeperiodUsage] = {}

        for e in recurring_events:
            ice = ICalEvent(e)
            exceptions = {**exceptions, **ice.to_timeperiod_exception()}

    assert exceptions["2024-08-01"] == (("12:00", "24:00"))
    assert exceptions["2024-08-10"] == (("12:00", "24:00"))
    assert exceptions["2024-08-11"] == (("00:00", "24:00"))
    assert exceptions["2024-08-12"] == (("00:00", "24:00"))
    assert exceptions["2024-08-13"] == (("00:00", "24:00"))


def test_convert_partial_end_day_exceptions() -> None:
    data = [
        {
            "dtstart": "VALUE=DATE:20240801",
            "dtend": "TZID=UTC:20240801T120000Z",
            "summary": "Single day event",
            "description": "Single day event",
        },
        {
            "dtstart": "VALUE=DATE:20240810",
            "dtend": "TZID=UTC:20240813T120000Z",
            "summary": "4 days event",
            "description": "4 days event",
        },
    ]

    with time_machine.travel(datetime.datetime(2024, 4, 15, tzinfo=ZoneInfo("UTC"))):
        ical_string = create_ical_file(data)
        cal_obj: Calendar = Calendar.from_ical(ical_string)  # type: ignore[assignment]

        recurring_events = recurring_ical_events.of(cal_obj).between("20240415", "20250101")

        exceptions: dict[str, TimeperiodUsage] = {}

        for e in recurring_events:
            ice = ICalEvent(e)
            exceptions = {**exceptions, **ice.to_timeperiod_exception()}

    assert exceptions["2024-08-01"] == (("00:00", "12:00"))
    assert exceptions["2024-08-10"] == (("00:00", "24:00"))
    assert exceptions["2024-08-11"] == (("00:00", "24:00"))
    assert exceptions["2024-08-12"] == (("00:00", "24:00"))
    assert exceptions["2024-08-13"] == (("00:00", "12:00"))


def test_convert_partial_days_exceptions() -> None:
    data = [
        {
            "dtstart": "TZID=UTC:20240801T090000Z",
            "dtend": "TZID=UTC:20240801T180000Z",
            "summary": "Working hours",
            "description": "Working hours",
        },
    ]

    with time_machine.travel(datetime.datetime(2024, 4, 15, tzinfo=ZoneInfo("UTC"))):
        ical_string = create_ical_file(data)
        cal_obj: Calendar = Calendar.from_ical(ical_string)  # type: ignore[assignment]

        recurring_events = recurring_ical_events.of(cal_obj).between("20240415", "20250101")

        exceptions: dict[str, TimeperiodUsage] = {}

        for e in recurring_events:
            ice = ICalEvent(e)
            exceptions = {**exceptions, **ice.to_timeperiod_exception()}

    assert exceptions["2024-08-01"] == (("09:00", "18:00"))


def test_convert_multiple_partial_days_exceptions() -> None:
    data = [
        {
            "dtstart": "TZID=UTC:20240801T220000Z",
            "dtend": "TZID=UTC:20240802T080000Z",
            "summary": "Maintenance window",
            "description": "Maintenance window",
        },
    ]

    with time_machine.travel(datetime.datetime(2024, 4, 15, tzinfo=ZoneInfo("UTC"))):
        ical_string = create_ical_file(data)
        cal_obj: Calendar = Calendar.from_ical(ical_string)  # type: ignore[assignment]

        recurring_events = recurring_ical_events.of(cal_obj).between("20240415", "20250101")

        exceptions: dict[str, TimeperiodUsage] = {}

        for e in recurring_events:
            ice = ICalEvent(e)
            exceptions = {**exceptions, **ice.to_timeperiod_exception()}

    assert exceptions["2024-08-01"] == (("22:00", "24:00"))
    assert exceptions["2024-08-02"] == (("00:00", "08:00"))


def test_convert_multiple_ranges_per_days_exceptions() -> None:
    examine_date = "2024-08-01"
    data = [
        {
            "dtstart": "VALUE=DATE:20240801",
            "dtend": "TZID=UTC:20240801T080000Z",
            "summary": "Before working hours",
            "description": "Before working hours",
        },
        {
            "dtstart": "TZID=UTC:20240801T180000Z",
            "dtend": "VALUE=DATE:20240802",
            "summary": "After working hours",
            "description": "After working hours",
        },
    ]

    with time_machine.travel(datetime.datetime(2024, 4, 15, tzinfo=ZoneInfo("UTC"))):
        ical_string = create_ical_file(data)
        cal_obj: Calendar = Calendar.from_ical(ical_string)  # type: ignore[assignment]

        recurring_events = recurring_ical_events.of(cal_obj).between("20240415", "20250101")

        exception_map: dict[str, list[TimeperiodUsage]] = {}
        for e in recurring_events:
            ice = ICalEvent(e)
            timerange = ice.to_timeperiod_exception()[examine_date]

            if existing_event := exception_map.get(examine_date):
                existing_event.append(timerange)
                continue
            exception_map[examine_date] = [timerange]

    assert exception_map[examine_date] == [("00:00", "08:00"), ("18:00", "24:00")]


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
