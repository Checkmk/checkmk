#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info

from cmk.agent_based.v2 import any_of, contains, SNMPTree, StringTable


def inventory_blade_powermod(info):
    return [(line[0], {}) for line in info if line[1] == "1"]


def check_blade_powermod(index, _no_param, info):
    for line in info:
        if line[0] == index:
            present, status, text = line[1:]
            if present != "1":
                return (2, "Not present")
            if status != "1":
                return (2, "%s" % text)
            return (0, "%s" % text)
    return (3, "Module %s not found in SNMP info" % index)


def parse_blade_powermod(string_table: StringTable) -> StringTable:
    return string_table


check_info["blade_powermod"] = LegacyCheckDefinition(
    parse_function=parse_blade_powermod,
    detect=any_of(
        contains(".1.3.6.1.2.1.1.1.0", "BladeCenter Management Module"),
        contains(".1.3.6.1.2.1.1.1.0", "BladeCenter Advanced Management Module"),
    ),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.2.3.51.2.2.4.1.1",
        oids=["1", "2", "3", "4"],
    ),
    service_name="Power Module %s",
    discovery_function=inventory_blade_powermod,
    check_function=check_blade_powermod,
)
