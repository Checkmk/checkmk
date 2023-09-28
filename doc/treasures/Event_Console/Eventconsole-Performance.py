#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


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
    return (
        "%.1f %% " % busy,
        "<table><tr>"
        + perfometer_td(busytd, color)
        + perfometer_td(freetd, "#ffffff")
        + "</tr></table>",
    )


perfometers["get_event_status"] = perfometer_get_event_status
