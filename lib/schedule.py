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

import time


def last_scheduled_time(period, timeofday):
    return __scheduled_time(period, timeofday, "last")


def next_scheduled_time(period, timeofday):
    return __scheduled_time(period, timeofday, "next")


def __scheduled_time(period, timeofday, how):
    if how == "last":
        comp = lambda a, b: a > b
        add = 1
    elif how == "next":
        comp = lambda a, b: a < b
        add = -1
    else:
        raise NotImplementedError()

    now = time.time()

    year, month, mday, hour, minute, second, wday = range(7)

    # Get the current time according to our timezone
    brokentime = list(time.localtime(now))

    # Enter the time of the day into the struct
    brokentime[hour]   = timeofday[0] # hours
    brokentime[minute] = timeofday[1] # minutes
    brokentime[second] = 0            # seconds

    if period == "day":
        ref_time = time.mktime(brokentime)
        if comp(ref_time, now): # in the future: substract one day
            ref_time -= 24 * 3600 * add

    elif period[0] == "week":
        ref_time = time.mktime(brokentime)
        daydiff = period[1] - brokentime[wday] # wday
        ref_time += daydiff * 24 * 3600
        if comp(ref_time, now): # in the future: substract one week
            ref_time -= 7 * 24 * 3600 * add

    elif period[0] == "month_begin":
        brokentime[mday] = period[1] # mday
        ref_time = time.mktime(brokentime)
        if comp(ref_time, now): # in the future: go back to previous month
            brokentime[month] -= 1 * add
            if brokentime[month] == 0:
                brokentime[month] = 12
                brokentime[year] -= 1
            elif brokentime[month] == 13:
                brokentime[month] = 1
                brokentime[year] += 1
            ref_time = time.mktime(brokentime)

    elif period[0] == "month_end":
        minus_mday = period[1]
        # Find last day in this month.
        brokentime[mday] = 1
        brokentime[month] += 1
        if brokentime[month] == 13:
            brokentime[month] = 1
            brokentime[year] += 1
        ref_time = time.mktime(brokentime) - minus_mday * 24 * 3600
        if comp(ref_time, now): # switch to previous/next month
            brokentime = list(time.localtime(ref_time))
            brokentime[mday] = 1
            if how == "next":
                brokentime[month] += 1
                if brokentime[month] == 13:
                    brokentime[year] += 1

            ref_time = time.mktime(brokentime) - minus_mday * 24 * 3600 * add

    # Due to the date shift a change in the timezone could have
    # happened. Make sure hour is correctly set again
    brokentime = list(time.localtime(ref_time))
    brokentime[hour] = timeofday[0]
    ref_time = time.mktime(brokentime)
    return ref_time
