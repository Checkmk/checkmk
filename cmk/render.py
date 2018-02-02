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

"""This module contains functions that transform Python values into
text representations optimized for human beings - with optional localization.
The resulting strings are not ment to be parsed into values again later. They
are just for optical output purposes."""

# THIS IS STILL EXPERIMENTAL

import time

# TODO: Clean this up one day by using the way recommended by gettext.
# (See https://docs.python.org/2/library/gettext.html). For this we
# need the path to the locale files here.
try:
    _
except NameError:
    _ = lambda x: x # Fake i18n when not available


def date(timestamp):
    return time.strftime("%Y-%m-%d", time.localtime(timestamp))


def date_and_time(timestamp):
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(timestamp))


def time_of_day(timestamp):
    return time.strftime("%H:%M:%S", time.localtime(timestamp))


def timespan(seconds):
    hours, secs = divmod(seconds, 3600)
    mins, secs = divmod(secs, 60)
    return "%d:%02d:%02d" % (hours, mins, secs)


def time_since(timestamp):
    return timespan(time.time() - timestamp)


def approx_age(secs):
    """Format time difference seconds into approximated human readable text"""

    if secs < 240:
        return "%d sec" % secs

    mins = secs / 60
    if mins < 120:
        return "%d min" % mins

    hours, mins = divmod(mins, 60)
    if hours < 12 and mins > 0:
        return "%d hours %d min" % (hours, mins)
    elif hours < 48:
        return "%d hours" % hours

    days, hours = divmod(hours, 24)
    if days < 7 and hours > 0:
        return "%d days %d hours" % (days, hours)

    return "%d days" % days


def bytes(b, base=1024.0, bytefrac=True, unit="B"):
    """Formats byte values to be used in texts for humans.

    Takes bytes as integer and returns a string which represents the bytes in a
    more human readable form scaled to TB/GB/MB/KB. The unit parameter simply
    changes the returned string, but does not interfere with any calcluations."""
    base = float(base)

    # Handle negative bytes correctly
    prefix = ''
    if b < 0:
        prefix = '-'
        b *= -1

    if b >= base * base * base * base:
        return '%s%.2f T%s' % (prefix, b / base / base / base / base, unit)
    elif b >= base * base * base:
        return '%s%.2f G%s' % (prefix, b / base / base / base, unit)
    elif b >= base * base:
        return '%s%.2f M%s' % (prefix, b / base / base, unit)
    elif b >= base:
        return '%s%.2f k%s' % (prefix, b / base, unit)
    elif bytefrac:
        return '%s%.2f %s' % (prefix, b, unit)
    else: # Omit byte fractions
        return '%s%.0f %s' % (prefix, b, unit)


# Precise size of a file - separated decimal separator
# 1234 -> "1234"
# 12345 => "12,345"
def filesize(size):
    dec_sep = ","
    if size < 10000:
        return str(size)
    elif size < 1000000:
        return str(size)[:-3] + dec_sep + str(size)[-3:]
    elif size < 1000000000:
        return str(size)[:-6] + dec_sep + str(size)[-6:-3] + dec_sep + str(size)[-3:]
    else:
        return str(size)[:-9] + dec_sep + str(size)[-9:-6] + dec_sep + str(size)[-6:-3] + dec_sep + str(size)[-3:]
