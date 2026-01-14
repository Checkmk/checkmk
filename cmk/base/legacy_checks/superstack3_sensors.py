#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import contains, SNMPTree, StringTable

check_info = {}


def discover_superstack3_sensors(info):
    return [(line[0], None) for line in info if line[1] != "not present"]


def check_superstack3_sensors(item, params, info):
    for name, state in info:
        if name == item:
            if state == "failure":
                return (2, "status is %s" % state)
            if state == "operational":
                return (0, "status is %s" % state)
            return (1, "status is %s" % state)
    return (3, "UNKOWN - sensor not found")


def parse_superstack3_sensors(string_table: StringTable) -> StringTable:
    return string_table


check_info["superstack3_sensors"] = LegacyCheckDefinition(
    name="superstack3_sensors",
    parse_function=parse_superstack3_sensors,
    detect=contains(".1.3.6.1.2.1.1.1.0", "3com superstack 3"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.43.43.1.1",
        oids=["7", "10"],
    ),
    service_name="%s",
    discovery_function=discover_superstack3_sensors,
    check_function=check_superstack3_sensors,
)
