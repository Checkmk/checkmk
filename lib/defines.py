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

"""This module serves constants which are needed in several components
of Check_MK."""

# TODO: Clean this up one day by using the way recommended by gettext.
# (See https://docs.python.org/2/library/gettext.html). For this we
# need the path to the locale files here.
try:
    _
except NameError:
    _ = lambda x: x # Fake i18n when not available


# TODO: Investigate Check_MK code for more defines and other places
#       where similar strucures are defined and use the things from
#       here or move new stuff to this module.

# TODO: Rename to service_state_names()
def core_state_names():
    return {
        -1 : _("NODATA"),
         0 : _("OK"),
         1 : _("WARNING"),
         2 : _("CRITICAL"),
         3 : _("UNKNOWN"),
    }


def service_state_name(state_num, deflt=""):
    return core_state_names().get(state_num, deflt)


def short_service_state_names():
    return {
        -1: _("PEND"),
         0: _("OK"),
         1: _("WARN"),
         2: _("CRIT"),
         3: _("UNKN"),
    }


def short_service_state_name(state_num, deflt=""):
    return short_service_state_names().get(state_num, deflt)


def host_state_name(state_num, deflt=""):
    states = {
        0: _("UP"),
        1: _("DOWN"),
        2: _("UNREACHABLE"),
    }
    return states.get(state_num, deflt)


def short_host_state_name(state_num, deflt=""):
    states = {
        0: _("UP"),
        1: _("DOWN"),
        2: _("UNREACH")
    }
    return states.get(state_num, deflt)


def weekday_name(day_num):
    return weekdays()[day_num]


def weekdays():
    return {
       0: _("Monday"),
       1: _("Tuesday"),
       2: _("Wednesday"),
       3: _("Thursday"),
       4: _("Friday"),
       5: _("Saturday"),
       6: _("Sunday"),
    }


def interface_oper_state_name(state_num, deflt=""):
    return interface_oper_states().get(state_num, deflt)


def interface_oper_states():
    return {
        1: _("up"),
        2: _("down"),
        3: _("testing"),
        4: _("unknown"),
        5: _("dormant"),
        6: _("not present"),
        7: _("lower layer down"),
        8: _("degraded"),    # artificial, not official
        9: _("admin down"),  # artificial, not official
    }
