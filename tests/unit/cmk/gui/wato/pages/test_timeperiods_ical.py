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

from cmk.gui.wato.pages.timeperiods import TimeperiodUsage
from cmk.gui.wato.pages.timeperiods_ical import ICalEvent, import_ical

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


_NOW = datetime.datetime(2027, 1, 1)
_ONE_YEAR = datetime.timedelta(days=365)


def _calendar(*events: str, properties: str = "") -> bytes:
    vevents = "".join(
        f"BEGIN:VEVENT\nUID:event-{index}\n{event}\nEND:VEVENT\n"
        for index, event in enumerate(events)
    )
    return f"BEGIN:VCALENDAR\nVERSION:2.0\n{properties}{vevents}END:VCALENDAR\n".encode()


def test_import_ical_expands_recurring_events() -> None:
    content = _calendar("DTSTART:20270105T090000\nDTEND:20270105T120000\nRRULE:FREQ=WEEKLY;COUNT=3")

    result = import_ical(content, filename="cal.ics", now=_NOW, horizon=_ONE_YEAR)

    assert result.exceptions == {
        "2027-01-05": [("09:00", "12:00")],
        "2027-01-12": [("09:00", "12:00")],
        "2027-01-19": [("09:00", "12:00")],
    }


def test_import_ical_ignores_events_outside_horizon() -> None:
    content = _calendar(
        "DTSTART;VALUE=DATE:20270110\nDTEND;VALUE=DATE:20270111",
        "DTSTART;VALUE=DATE:20280110\nDTEND;VALUE=DATE:20280111",
    )

    result = import_ical(content, filename="cal.ics", now=_NOW, horizon=_ONE_YEAR)

    assert result.exceptions == {"2027-01-10": [("00:00", "24:00")]}


def test_import_ical_collects_time_ranges_of_a_day() -> None:
    content = _calendar(
        "DTSTART:20270105T080000\nDTEND:20270105T090000",
        "DTSTART:20270105T180000\nDTEND:20270105T190000",
    )

    result = import_ical(content, filename="cal.ics", now=_NOW, horizon=_ONE_YEAR)

    assert sorted(result.exceptions["2027-01-05"]) == [("08:00", "09:00"), ("18:00", "19:00")]


def test_import_ical_full_day_event_replaces_other_time_ranges_of_the_day() -> None:
    content = _calendar(
        "DTSTART:20270105T080000\nDTEND:20270105T090000",
        "DTSTART;VALUE=DATE:20270105\nDTEND;VALUE=DATE:20270106",
    )

    result = import_ical(content, filename="cal.ics", now=_NOW, horizon=_ONE_YEAR)

    assert result.exceptions == {"2027-01-05": [("00:00", "24:00")]}


# fmt: off
@pytest.mark.parametrize(
    ("properties", "expected_alias"),
    [
        pytest.param("X-WR-CALDESC:Description\nX-WR-CALNAME:Name\n", "Description", id="description first"),
        pytest.param("X-WR-CALNAME:Name\n", "Name", id="name without description"),
        pytest.param("", "cal.ics", id="file name without both"),
    ],
)
# fmt: on
def test_import_ical_alias_prefers_description_then_name_then_file_name(properties: str, expected_alias: str) -> None:
    content = _calendar(properties=properties)

    result = import_ical(content, filename="cal.ics", now=_NOW, horizon=_ONE_YEAR)

    assert result.alias == expected_alias
