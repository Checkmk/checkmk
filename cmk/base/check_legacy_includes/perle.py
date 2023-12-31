#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


def perle_check_alarms(alarms_str):
    state = 0
    alarminfo = ""
    if int(alarms_str) > 0:
        state = 2
        alarminfo += " (User intervention is needed to resolve the outstanding alarms)"

    return state, f"Alarms: {alarms_str}{alarminfo}"
