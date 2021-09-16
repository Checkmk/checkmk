#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package

from typing import Optional

from .agent_based_api.v1 import register, SNMPTree
from .agent_based_api.v1.type_defs import StringTable
from .utils.ups import (
    Battery,
    CHECK_DEFAULT_PARAMETERS,
    check_ups_capacity,
    DETECT_UPS_GENERIC,
    discover_ups_capacity,
    optional_int,
)


def parse_ups_capacity(string_table: StringTable) -> Optional[Battery]:
    return (
        Battery(
            seconds_left=optional_int(string_table[0][0], factor=60),
            percent_charged=optional_int(string_table[0][1]),
        )
        if string_table
        else None
    )


def parse_ups_seconds_on_battery(string_table: StringTable) -> Optional[Battery]:
    return (
        Battery(
            seconds_on_bat=optional_int(string_table[0][0]),
        )
        if string_table
        else None
    )


register.snmp_section(
    name="ups_battery_capacity",
    parse_function=parse_ups_capacity,
    fetch=SNMPTree(
        base=".1.3.6.1.2.1.33.1.2",
        oids=[
            "3.0",  # Remaining battery backup time  [min], int
            "4.0",  # Battery charge level           [%], int
        ],
    ),
    detect=DETECT_UPS_GENERIC,
)

register.snmp_section(
    name="ups_seconds_on_battery",
    parse_function=parse_ups_seconds_on_battery,
    fetch=SNMPTree(
        base=".1.3.6.1.2.1.33.1.2",
        oids=[
            "2.0",  # Seconds on battery             [sec], int | "0" == "not on battery"
        ],
    ),
    detect=DETECT_UPS_GENERIC,
)

register.check_plugin(
    name="ups_capacity",
    sections=["ups_battery_capacity", "ups_on_battery", "ups_seconds_on_battery"],
    service_name="Battery capacity",
    check_function=check_ups_capacity,
    discovery_function=discover_ups_capacity,
    check_ruleset_name="ups_capacity",
    check_default_parameters=dict(CHECK_DEFAULT_PARAMETERS),
)
