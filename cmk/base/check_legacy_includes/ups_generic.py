#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# type: ignore[list-item,import,assignment,misc,operator]  # TODO: see which are needed in this file


def ups_generic_scan_function(oid):
    return (
        oid(".1.3.6.1.2.1.1.2.0")
        in [
            ".1.3.6.1.4.1.232.165.3",
            ".1.3.6.1.4.1.476.1.42",
            ".1.3.6.1.4.1.534.1",
            ".1.3.6.1.4.1.8072.3.2.10",
            ".1.3.6.1.4.1.2254.2.5",
            ".1.3.6.1.4.1.12551.4.0",
        ]
        or oid(".1.3.6.1.2.1.1.2.0").startswith(".1.3.6.1.2.1.33")
        or oid(".1.3.6.1.2.1.1.2.0").startswith(".1.3.6.1.4.1.534.2")
        or oid(".1.3.6.1.2.1.1.2.0").startswith(".1.3.6.1.4.1.5491")
        or oid(".1.3.6.1.2.1.1.2.0").startswith(".1.3.6.1.4.1.705.1")
        or oid(".1.3.6.1.2.1.1.2.0").startswith(".1.3.6.1.4.1.818.1.100.1")
        or oid(".1.3.6.1.2.1.1.2.0").startswith(".1.3.6.1.4.1.935")
    )


def discovery_ups_generic(info, default_levels_name):
    return [
        (idx, default_levels_name)  #
        for idx, raw_voltage, _raw_value in info  #
        if raw_voltage and int(raw_voltage)
    ]
