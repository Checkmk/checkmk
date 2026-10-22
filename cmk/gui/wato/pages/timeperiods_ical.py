#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="comparison-overlap"
# mypy: disable-error-code="no-any-return"

"""Converts the events of an iCalendar file to time period exceptions

This is kept separate from the time period modes, so that the iCalendar libraries are only loaded
when an iCalendar file is imported.
"""

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import override

import recurring_ical_events
from icalendar import Calendar, Event
from icalendar.prop import vDDDTypes


@dataclass(frozen=True)
class ICalImport:
    alias: str
    exceptions: dict[str, list[tuple[str, str]]]
    """The time ranges of each day with an event, by date (YYYY-MM-DD)"""


def import_ical(content: bytes, *, filename: str, now: datetime, horizon: timedelta) -> ICalImport:
    """Collect the events of the iCalendar file between now and now + horizon"""
    # The types-icalendar stubs only accept str, icalendar itself also accepts bytes
    cal_obj: Calendar = Calendar.from_ical(content)  # type: ignore[call-overload]

    exception_map: dict[str, list[tuple[str, str]]] = {}
    for e in recurring_ical_events.of(cal_obj).between(now, now + horizon):
        ice = ICalEvent(e)
        if ice.dtstart_dt is None:
            continue  # type: ignore[unreachable]

        exceptions = ice.to_timeperiod_exception()
        for dt, timerange in exceptions.items():
            if existing_event := exception_map.get(dt):
                existing_event.append(timerange)
                continue
            exception_map[dt] = [timerange]

    # If a time period exception has the full day, we can ignore the others (if available)
    for timeranges in exception_map.values():
        if ("00:00", "24:00") in timeranges:
            timeranges[:] = [("00:00", "24:00")]

    return ICalImport(
        alias=str(cal_obj.get("X-WR-CALDESC", cal_obj.get("X-WR-CALNAME", filename))),
        exceptions=exception_map,
    )


class ICalEvent(Event):
    def __init__(self, event: Event):
        super().__init__(**event)
        self.time_ranges: list[tuple[str, str]] = []

    def _as_datetime(self, key: str) -> datetime:
        if key not in self:
            raise ValueError(f"Event obj doesn't have the key {key}")

        vddd: vDDDTypes = self[key]
        dt = vddd.dt

        if isinstance(dt, datetime):
            return dt.astimezone()

        if isinstance(dt, date):
            return datetime.combine(dt, datetime.min.time()).astimezone()

        raise ValueError(f"Error getting datetime obj for the key: {key}")

    @property
    def dtstart_dt(self) -> datetime:
        return self._as_datetime("DTSTART")

    @property
    def dtstart_str(self) -> str:
        return self.dtstart_dt.strftime("%Y-%m-%d")

    @property
    def _dtend(self) -> datetime:
        return self._as_datetime("DTEND")

    @property
    def _description(self) -> str:
        if "DESCRIPTION" not in self:
            return ""
        return self.decoded("DESCRIPTION").decode("UTF-8")

    @property
    def summary(self) -> str:
        if "SUMMARY" not in self:
            return self._description
        return self.decoded("SUMMARY").decode("UTF-8")

    @property
    def _duration(self) -> timedelta:
        if "DURATION" in self:
            dur: vDDDTypes = self["DURATION"]
            if isinstance(dur.dt, timedelta):
                return dur.dt

        return self._dtend - self.dtstart_dt

    @property
    def _timerange_to(self) -> str:
        duration = self._duration
        if duration.days >= 1 and duration.seconds == 0 and duration.microseconds == 0:
            return "24:00"

        return (self.dtstart_dt + self._duration).strftime("%H:%M")

    @property
    def timerange(self) -> tuple[str, str]:
        return self.dtstart_dt.strftime("%H:%M"), self._timerange_to

    @property
    def timeranges(self) -> set[tuple[str, str]]:
        self.time_ranges.append(self.timerange)
        if ("00:00", "24:00") in self.time_ranges:
            return {("00:00", "24:00")}
        return set(self.time_ranges)

    def add_timerange(self, new_timerange: tuple[str, str]) -> None:
        self.time_ranges.append(new_timerange)

    @override
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({super().__repr__()})"

    def to_timeperiod_exception(self) -> dict[str, tuple[str, str]]:
        """An event can take several days. Moreover, it does not necessarily have to take up the whole day.
        This method returns a dict that relates each of the days involved to the corresponding time slot.

        Examples:
        From 2024-08-01 00:00
        To 2024-08-02 00:00:00
        Output {'2024-08-01': ("00:00", "24:00")}

        From 2024-08-01 12:00:00
        To 2024-08-03 12:00:00
        Output {'2024-08-01': ("12:00", "24:00"), '2024-08-02': ("00:00", "24:00"), '2024-8-03': ("00:00", "12:00")}

        From 2024-08-01 09:00
        To 2024-08-01 18:00
        Output {'2024-08-01': ("09:00", "18:00")}

        """
        start_date = self.dtstart_dt
        event_lenght = self._duration
        end_date = start_date + event_lenght
        end_date_str = end_date.strftime("%Y-%m-%d")

        result: dict[str, tuple[str, str]] = {}
        current_day = start_date
        current_time_start = start_date.strftime("%H:%M")
        current_time_end = "24:00"

        while current_day.date() <= end_date.date():
            current_day_str = current_day.strftime("%Y-%m-%d")
            if current_day_str == end_date_str and (end_date.hour == 0 and end_date.minute == 0):
                break

            if current_day_str == end_date_str:
                current_time_end = end_date.strftime("%H:%M")

            result[current_day_str] = (current_time_start, current_time_end)
            current_day += timedelta(days=1)
            current_time_start = "00:00"

        return result
