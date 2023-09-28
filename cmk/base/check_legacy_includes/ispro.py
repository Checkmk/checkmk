#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


def ispro_sensors_alarm_states(status):
    return {
        "1": (3, "unknown"),
        "2": (1, "disable"),
        "3": (0, "normal"),
        "4": (1, "below low warning"),
        "5": (2, "below low critical"),
        "6": (1, "above high warning"),
        "7": (2, "above high critical"),
    }.get(status, (3, "unexpected(%s)" % status))
