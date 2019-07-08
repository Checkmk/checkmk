#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2016             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# The official homepage is at http://mathias-kettner.de/check_mk.
#
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

# Computes for a scheduling entry the last/next time that this entry
# should have run or will be run. Such a scheduling entry is specified
# by a period specification as produced by the SchedulePeriod() valuespec
# and a timeofday specification which is a two element tuple of hours and minutes

import abc
import datetime
import time

from dateutil.relativedelta import relativedelta
from dateutil.rrule import rrule, DAILY, WEEKLY, MONTHLY


class Schedule(object):
    """
    Abstract base class for schedules. A default implementation
    for the last and next event at a given datetime are provided.
    Subclasses have to define the class attribute _delta and the
    instance attribute _rule.
    """
    __metaclass__ = abc.ABCMeta

    @abc.abstractproperty
    def rule(self):
        pass

    @abc.abstractproperty
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
        if not 0 <= weekday <= 6:
            raise ValueError('weekday must be between 0 and 6')
        self._rule = rrule(WEEKLY,
                           byweekday=weekday,
                           byhour=timeofday.hour,
                           byminute=timeofday.minute,
                           bysecond=0)

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
        if not 1 <= day <= 31:
            raise ValueError('day must be between 1 and 31')
        self._rule = rrule(MONTHLY,
                           bymonthday=day,
                           byhour=timeofday.hour,
                           byminute=timeofday.minute,
                           bysecond=0)

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
        if not 1 <= days_from_end <= 31:
            raise ValueError('days_from_end must be between 1 and 31')
        day = -days_from_end
        self._rule = rrule(MONTHLY,
                           bymonthday=day,
                           byhour=timeofday.hour,
                           byminute=timeofday.minute,
                           bysecond=0)

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
        schedule = DaySchedule(t)
    elif period[0] == "week":
        weekday = period[1]
        schedule = WeekSchedule(weekday, t)
    elif period[0] == "month_begin":
        day = period[1]
        schedule = StartMonthSchedule(day, t)
    elif period[0] == "month_end":
        days_from_end = period[1]
        schedule = EndMonthSchedule(days_from_end, t)
    else:
        raise ValueError('Unknown period')

    return schedule


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
