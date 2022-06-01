#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.base.plugins.agent_based.utils.liebert import parse_liebert, parse_liebert_without_unit


def parse_liebert_wrapper(info, type_func=float):
    # This function is needed to convert the info data type
    # to the target data type of the new check API, StringTable
    return parse_liebert([info], type_func)


def parse_liebert_without_unit_wrapper(info, type_func=float):
    # This function is needed to convert the info data type
    # to the target data type of the new check API, StringTable
    return parse_liebert_without_unit([info], type_func)


def scan_liebert(oid):

    return oid(".1.3.6.1.2.1.1.2.0").startswith(".1.3.6.1.4.1.476.1.42")


def levels_liebert(value, warn, crit, sorting="upper"):
    state = 0
    if sorting == "upper":
        if value >= crit:
            state = 2
        elif value >= warn:
            state = 1
        else:
            state = 0
    elif sorting == "lower":
        if value <= crit:
            state = 2
        elif value <= warn:
            state = 1
        else:
            state = 0

    return state


def check_temp_unit(output):
    value = float(output[0])
    unit = output[1]
    if unit == "deg F":
        value = 5.0 / 9.0 * (value - 32)

    return value
