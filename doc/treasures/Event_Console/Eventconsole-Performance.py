#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# Copyright by Mathias Kettner and Mathias Kettner GmbH.  All rights reserved.
#
# Check_MK is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.
#
# Check_MK is  distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY;  without even the implied warranty of
# MERCHANTABILITY  or  FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have  received  a copy of the  GNU  General Public
# License along with Check_MK.  If  not, email to mk@mathias-kettner.de
# or write to the postal address provided at www.mathias-kettner.de


def perfometer_get_event_status(row, check_command, perfdata):
    busy = float(perfdata[2][1]) 
    warn = float(perfdata[2][3])
    crit = float(perfdata[2][4])
    if busy > crit:
         color = "#ff0000"
    elif busy > warn:
         color = "#ffff00"
    else:
         color = "#00ff00" 
    if busy > 100:
         busytd = 100
         freetd = 0
    else:
         busytd = busy
         freetd = 100 - busy
    return "%.1f %% " % busy, \
        '<table><tr>' \
        + perfometer_td(busytd, color) \
        + perfometer_td(freetd, "#ffffff") \
        + '</tr></table>'

perfometers["get_event_status"]           = perfometer_get_event_status
