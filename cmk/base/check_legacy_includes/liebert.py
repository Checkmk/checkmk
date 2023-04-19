#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.base.plugins.agent_based.utils.liebert import (
    parse_liebert,
    parse_liebert_without_unit,
    temperature_to_celsius,
)


def parse_liebert_wrapper(info, type_func=float):
    # This function is needed to convert the info data type
    # to the target data type of the new check API, StringTable
    return parse_liebert([info], type_func)


def parse_liebert_without_unit_wrapper(info, type_func=float):
    # This function is needed to convert the info data type
    # to the target data type of the new check API, StringTable
    return parse_liebert_without_unit([info], type_func)


def check_temp_unit(output):
    return temperature_to_celsius(float(output[0]), output[1])
