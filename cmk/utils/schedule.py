#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
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
    def rule(self) -> rrule:
        pass

    @property
    @abc.abstractmethod
    def delta(self) -> relativedelta:
        pass

    def next(self, t):
        return self.rule.replace(dtstart=t).after(t)

    def last(self, t):
        from_ = t + self.delta
        return self.rule.replace(dtstart=from_, until=t).before(t)


class DaySchedule(Schedule):
    """
    A daily schedule.
    """

    def __init__(self, timeofday: datetime.time) -> None:
        super().__init__()
        self._rule = rrule(DAILY, byhour=timeofday.hour, byminute=timeofday.minute, bysecond=0)

    @property
    def rule(self) -> rrule:
        return self._rule

    @property
    def delta(self) -> relativedelta:
        return relativedelta(days=-1)


class WeekSchedule(Schedule):
    """
    A weekly schedule.
    """

    def __init__(self, weekday: int, timeofday: datetime.time) -> None:
        super().__init__()
        if not 0 <= weekday <= 6:
            raise ValueError("weekday must be between 0 and 6")
        self._rule = rrule(
            WEEKLY, byweekday=weekday, byhour=timeofday.hour, byminute=timeofday.minute, bysecond=0
        )

    @property
    def rule(self) -> rrule:
        return self._rule

    @property
    def delta(self) -> relativedelta:
        return relativedelta(weeks=-1)


class StartMonthSchedule(Schedule):
    """
    A monthly schedule initialized relatively to the first day of the month.
    """

    def __init__(self, day: int, timeofday: datetime.time) -> None:
        super().__init__()
        if not 1 <= day <= 31:
            raise ValueError("day must be between 1 and 31")
        self._rule = rrule(
            MONTHLY, bymonthday=day, byhour=timeofday.hour, byminute=timeofday.minute, bysecond=0
        )

    @property
    def rule(self) -> rrule:
        return self._rule

    @property
    def delta(self) -> relativedelta:
        return relativedelta(months=-2)


class EndMonthSchedule(Schedule):
    """
    A monthly schedule initialized relatively to the last day of the month.
    """

    def __init__(self, days_from_end: int, timeofday: datetime.time) -> None:
        super().__init__()
        if not 1 <= days_from_end <= 31:
            raise ValueError("days_from_end must be between 1 and 31")
        day = -days_from_end
        self._rule = rrule(
            MONTHLY, bymonthday=day, byhour=timeofday.hour, byminute=timeofday.minute, bysecond=0
        )

    @property
    def rule(self) -> rrule:
        return self._rule

    @property
    def delta(self) -> relativedelta:
        return relativedelta(months=-2)


def _get_schedule(period: str | tuple[str, int], timeofday: tuple[int, int]) -> Schedule:
    """
    Returns a schedule instance for a given period and timeofday.
    """
    t = datetime.time(*timeofday)

    if period == "day":
        return DaySchedule(t)
    assert isinstance(period, tuple)
    match period[0]:
        case "week":
            return WeekSchedule(period[1], t)
        case "month_begin":
            return StartMonthSchedule(period[1], t)
        case "month_end":
            return EndMonthSchedule(period[1], t)
    raise ValueError("Unknown period")


def last_scheduled_time(
    period: str | tuple[str, int], timeofday: tuple[int, int], dt: datetime.datetime | None = None
) -> float:
    if dt is None:
        dt = datetime.datetime.now()
    schedule = _get_schedule(period, timeofday)
    return time.mktime(schedule.last(dt).timetuple())


# Timeofday
def next_scheduled_time(
    period: str | tuple[str, int], timeofday: tuple[int, int], dt: datetime.datetime | None = None
) -> float:
    if dt is None:
        dt = datetime.datetime.now()
    schedule = _get_schedule(period, timeofday)
    return time.mktime(schedule.next(dt).timetuple())
