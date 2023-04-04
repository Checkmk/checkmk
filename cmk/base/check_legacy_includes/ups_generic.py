#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


def discovery_ups_generic(info, default_levels):
    return [
        (idx, default_levels)
        for idx, raw_voltage, _raw_value in info
        if raw_voltage and int(raw_voltage)
    ]
