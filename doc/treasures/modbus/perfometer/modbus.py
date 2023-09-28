#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Put this file into share/check_mk/web/plugins/perfometer


def perfometer_modbus_value(row, check_command, perf_data):
    value = int(perf_data[0][1])
    return perf_data[0][1], perfometer_logarithmic(value, value * 3, 2, "#3366cc")


perfometers["check_mk-modbus_value"] = perfometer_modbus_value
