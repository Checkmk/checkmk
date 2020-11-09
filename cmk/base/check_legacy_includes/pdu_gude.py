#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# type: ignore[var-annotated,list-item,import,assignment,misc,operator]  # TODO: see which are needed in this file
pdu_gude_default_levels = {
    "V": (220, 210),  # Volt
    "A": (15, 16),  # Ampere
    "W": (3500, 3600),  # Watt
}


def inventory_pdu_gude(info):
    if len(info) > 0:
        return [(x + 1, "pdu_gude_default_levels") for x in range(len(info))]


def check_pdu_gude(item, params, info):
    try:
        values = info[item - 1]
    except ValueError:
        yield 3, "No phase %d found in agent output" % item
        return

    units = {
        0: ("kWh", 1000),
        1: ("W", False),
        2: ("A", 1000),
        3: ("V", False),
        4: ("VA", False),
    }

    for pos, (unit, div) in units.items():
        value = float(values[pos])
        if div:
            value = value / div  # fixed: true-division
        infotext = "%.2f %s" % (value, unit)

        warn, crit = params.get(unit, (None, None))
        perfdata = [(unit, value, warn, crit)]
        status = 0

        if warn > crit:
            if value < crit:
                status = 2
            elif value < warn:
                status = 1

        else:
            if crit is not None and value > crit:
                status = 2
            elif warn is not None and value > warn:
                status = 1

        yield status, infotext, perfdata
