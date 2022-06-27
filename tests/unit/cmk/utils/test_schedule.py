#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime
import time

import cmk.utils.schedule as schedule


def test_day_schedule() -> None:
    s = schedule.DaySchedule(datetime.time(12, 30))
    now = datetime.datetime(2018, 3, 7, 10, 12, 32)

    next_expected = datetime.datetime(2018, 3, 7, 12, 30)
    assert s.next(now) == next_expected

    last_expected = datetime.datetime(2018, 3, 6, 12, 30)
    assert s.last(now) == last_expected


def test_day_schedule_with_same_datetime() -> None:
    s = schedule.DaySchedule(datetime.time(12, 30))
    now = datetime.datetime(2018, 3, 7, 12, 30)

    next_expected = datetime.datetime(2018, 3, 8, 12, 30)
    assert s.next(now) == next_expected

    last_expected = datetime.datetime(2018, 3, 6, 12, 30)
    assert s.last(now) == last_expected


def test_week_schedule() -> None:
    monday = 0
    s = schedule.WeekSchedule(monday, datetime.time(9, 0))
    now = datetime.datetime(2018, 3, 7, 10, 12, 32)

    next_expected = datetime.datetime(2018, 3, 12, 9, 0)
    assert s.next(now) == next_expected

    last_expected = datetime.datetime(2018, 3, 5, 9, 0)
    assert s.last(now) == last_expected


def test_week_schedule_with_same_day() -> None:
    wednesday = 2
    s = schedule.WeekSchedule(wednesday, datetime.time(12, 30))
    now = datetime.datetime(2018, 3, 7, 12, 29, 59, 999999)  # this is a wednesday

    next_expected = datetime.datetime(2018, 3, 7, 12, 30)
    assert s.next(now) == next_expected

    last_expected = datetime.datetime(2018, 2, 28, 12, 30)
    assert s.last(now) == last_expected


def test_startmonth_schedule() -> None:
    s = schedule.StartMonthSchedule(3, datetime.time(12, 30))
    now = datetime.datetime(2018, 3, 7, 10, 12, 32)

    next_expected = datetime.datetime(2018, 4, 3, 12, 30)
    assert s.next(now) == next_expected

    last_expected = datetime.datetime(2018, 3, 3, 12, 30)
    assert s.last(now) == last_expected


def test_startmonth_schedule_next_month_fewer_days() -> None:
    # Large days may lead to unexpected behaviour.
    # If day is to large months with fewer days are skipped.
    # This is conformant with the iCalendar RFC:
    # https://tools.ietf.org/html/rfc5545 (section 3.3.10).
    # For these cases the EndMonthSchedule should be used.
    s = schedule.StartMonthSchedule(31, datetime.time(12, 30))
    now = datetime.datetime(2018, 3, 31, 13, 00, 00)

    next_expected = datetime.datetime(2018, 5, 31, 12, 30)
    assert s.next(now) == next_expected

    last_expected = datetime.datetime(2018, 3, 31, 12, 30)
    assert s.last(now) == last_expected


def test_startmonth_schedule_with_large_day() -> None:
    # This test contains a switch to the daylight saving time
    # which was a problem in previous version.
    s = schedule.StartMonthSchedule(31, datetime.time(12, 30))
    now = datetime.datetime(2018, 3, 7, 10, 12, 32)

    next_expected = datetime.datetime(2018, 3, 31, 12, 30)
    assert s.next(now) == next_expected

    last_expected = datetime.datetime(2018, 1, 31, 12, 30)
    assert s.last(now) == last_expected


def test_startmonth_schedule_on_same_day() -> None:
    # If the actual time matches the schedule exactly the
    # the next date equals the actual time.
    s = schedule.StartMonthSchedule(7, datetime.time(12, 30))
    now = datetime.datetime(2018, 3, 7, 12, 30, 1)

    next_expected = datetime.datetime(2018, 4, 7, 12, 30)
    assert s.next(now) == next_expected

    last_expected = datetime.datetime(2018, 3, 7, 12, 30)
    assert s.last(now) == last_expected


def test_endmonth_schedule() -> None:
    s = schedule.EndMonthSchedule(1, datetime.time(12, 30))
    now = datetime.datetime(2018, 3, 7, 10, 12, 32)

    next_expected = datetime.datetime(2018, 3, 31, 12, 30)
    assert s.next(now) == next_expected

    last_expected = datetime.datetime(2018, 2, 28, 12, 30)
    assert s.last(now) == last_expected


def test_endmonth_schedule_two_days() -> None:
    # If the previous month has fewer days this has to be honored
    # by the EndMonthSchedule.
    s = schedule.EndMonthSchedule(3, datetime.time(12, 30))
    now = datetime.datetime(2018, 3, 7, 10, 12, 32)

    next_expected = datetime.datetime(2018, 3, 29, 12, 30)
    assert s.next(now) == next_expected

    last_expected = datetime.datetime(2018, 2, 26, 12, 30)
    assert s.last(now) == last_expected


def test_last_scheduled_time_month_start() -> None:
    result = schedule.last_scheduled_time(
        ["month_begin", 4], [12, 30], dt=datetime.datetime(2017, 2, 7, 10, 31, 52)
    )
    expected = time.mktime(datetime.datetime(2017, 2, 4, 12, 30).timetuple())
    assert result == expected


def test_next_scheduled_time_month_end() -> None:
    result = schedule.next_scheduled_time(
        ["month_end", 4], [12, 30], dt=datetime.datetime(2017, 1, 31, 10, 31, 52)
    )
    expected = time.mktime(datetime.datetime(2017, 2, 25, 12, 30).timetuple())
    assert result == expected
