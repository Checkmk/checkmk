#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2015             mk@mathias-kettner.de |
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


def perfometer_check_tcp(row, check_command, perfdata):
    time_ms = float(perfdata[0][1]) * 1000.0
    return "%.3f ms" % time_ms, \
        perfometer_logarithmic(time_ms, 1000, 10, "#20dd30")

perfometers["check-tcp"]           = perfometer_check_tcp
perfometers["check_tcp"]           = perfometer_check_tcp
perfometers["check_mk_active-tcp"] = perfometer_check_tcp

def perfometer_check_http(row, check_command, perfdata):
    try:
        time_ms = float(perfdata[0][1]) * 1000.0
    except:
        time_ms = 0
    return "%.1f ms" % time_ms, \
        perfometer_logarithmic(time_ms, 1000, 10, "#66ccff")

perfometers["check-http"] = perfometer_check_http
perfometers["check_http"] = perfometer_check_http
perfometers["check_mk_active-http"] = perfometer_check_http
