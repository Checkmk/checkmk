#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info

from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.plugins.lib.casa import DETECT_CASA


def inventory_casa_power(info):
    yield from ((str(idx), None) for idx in range(len(info)))


def check_casa_power(item, _no_params, info):
    unit_nr = int(item)
    if len(info) < unit_nr:
        return (3, "Power Supply %s not found in snmp output" % item)

    return {
        "0": (3, "Power supply - Unknown status (!)"),
        "1": (0, "Power supply OK"),
        "2": (0, "Power supply working under threshold (!)"),  # OK, backup power..
        "3": (1, "Power supply working over threshold (!)"),
        "4": (2, "Power Failure(!!)"),
    }.get(info[unit_nr][0])


def parse_casa_power(string_table: StringTable) -> StringTable:
    return string_table


check_info["casa_power"] = LegacyCheckDefinition(
    parse_function=parse_casa_power,
    detect=DETECT_CASA,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.20858.10.33.1.5.1",
        oids=["4"],
    ),
    service_name="Power %s",
    discovery_function=inventory_casa_power,
    check_function=check_casa_power,
)
