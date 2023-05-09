#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.plugins.views.perfometers import (
    perfometers,
    perfometer_logarithmic,
)


def perfometer_check_tcp(row, check_command, perfdata):
    time_ms = float(perfdata[0][1]) * 1000.0
    return "%.3f ms" % time_ms, \
        perfometer_logarithmic(time_ms, 1000, 10, "#20dd30")


perfometers["check-tcp"] = perfometer_check_tcp
perfometers["check_tcp"] = perfometer_check_tcp
perfometers["check_mk_active-tcp"] = perfometer_check_tcp


def perfometer_check_http(row, check_command, perfdata):
    try:
        time_ms = float(perfdata[0][1]) * 1000.0
    except (IndexError, ValueError):
        time_ms = 0
    return "%.1f ms" % time_ms, \
        perfometer_logarithmic(time_ms, 1000, 10, "#66ccff")


perfometers["check-http"] = perfometer_check_http
perfometers["check_http"] = perfometer_check_http
perfometers["check_mk_active-http"] = perfometer_check_http
