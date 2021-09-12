#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Computes for a scheduling entry the last/next time that this entry
# should have run or will be run. Such a scheduling entry is specified
# by a period specification as produced by the SchedulePeriod() valuespec
# and a timeofday specification which is a two element tuple of hours and minutes

import abc
import datetime
import time

from dateutil.relativedelta import relativedelta
from dateutil.rrule import DAILY, MONTHLY, rrule, WEEKLY


class Schedule(abc.ABC):
    """
    Abstract base class for schedules. A default implementation
    for the last and next event at a given datetime are provided.
    Subclasses have to define the class attribute _delta and the
    instance attribute _rule.
    """

    @property
    @abc.abstractmethod
    def rule(self):
        pass

    @property
    @abc.abstractmethod
    def delta(self):
        pass

    def next(self, t):
        return self.rule.replace(dtstart=t).after(t)

    def last(self, t):
        from_ = t + relativedelta(**self.delta)
        return self.rule.replace(dtstart=from_, until=t).before(t)


class DaySchedule(Schedule):
    """
    A daily schedule.
    """

    def __init__(self, timeofday):
        super().__init__()
        self._rule = rrule(DAILY, byhour=timeofday.hour, byminute=timeofday.minute, bysecond=0)

    @property
    def rule(self):
        return self._rule

    @property
    def delta(self):
        return {"days": -1}


class WeekSchedule(Schedule):
    """
    A weekly schedule.
    """

    def __init__(self, weekday, timeofday):
        super().__init__()
        if not 0 <= weekday <= 6:
            raise ValueError("weekday must be between 0 and 6")
        self._rule = rrule(
            WEEKLY, byweekday=weekday, byhour=timeofday.hour, byminute=timeofday.minute, bysecond=0
        )

    @property
    def rule(self):
        return self._rule

    @property
    def delta(self):
        return {"weeks": -1}


class StartMonthSchedule(Schedule):
    """
    A monthly schedule initialized relatively to the first day of the month.
    """

    def __init__(self, day, timeofday):
        super().__init__()
        if not 1 <= day <= 31:
            raise ValueError("day must be between 1 and 31")
        self._rule = rrule(
            MONTHLY, bymonthday=day, byhour=timeofday.hour, byminute=timeofday.minute, bysecond=0
        )

    @property
    def rule(self):
        return self._rule

    @property
    def delta(self):
        return {"months": -2}


class EndMonthSchedule(Schedule):
    """
    A monthly schedule initialized relatively to the last day of the month.
    """

    def __init__(self, days_from_end, timeofday):
        super().__init__()
        if not 1 <= days_from_end <= 31:
            raise ValueError("days_from_end must be between 1 and 31")
        day = -days_from_end
        self._rule = rrule(
            MONTHLY, bymonthday=day, byhour=timeofday.hour, byminute=timeofday.minute, bysecond=0
        )

    @property
    def rule(self):
        return self._rule

    @property
    def delta(self):
        return {"months": -2}


def _get_schedule(period, timeofday):
    """
    Returns a schedule instance for a given period and timeofday.
    """
    t = datetime.time(*timeofday)

    if period == "day":
        return DaySchedule(t)
    if period[0] == "week":
        weekday = period[1]
        return WeekSchedule(weekday, t)
    if period[0] == "month_begin":
        day = period[1]
        return StartMonthSchedule(day, t)
    if period[0] == "month_end":
        days_from_end = period[1]
        return EndMonthSchedule(days_from_end, t)
    raise ValueError("Unknown period")


def last_scheduled_time(period, timeofday, dt=None):
    if dt is None:
        dt = datetime.datetime.today()
    schedule = _get_schedule(period, timeofday)
    return time.mktime(schedule.last(dt).timetuple())


def next_scheduled_time(period, timeofday, dt=None):
    if dt is None:
        dt = datetime.datetime.today()
    schedule = _get_schedule(period, timeofday)
    return time.mktime(schedule.next(dt).timetuple())
