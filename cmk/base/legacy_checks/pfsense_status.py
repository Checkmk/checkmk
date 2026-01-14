#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import contains, SNMPTree, StringTable

check_info = {}


def discover_pfsense_status(info):
    if info:
        return [(None, None)]
    return []


def check_pfsense_status(_no_item, params, info):
    statusvar = info[0][0]
    if statusvar == "1":
        return 0, "Running"
    if statusvar == "2":
        return 2, "Not running"

    raise Exception("Unknown status value %s" % statusvar)


def parse_pfsense_status(string_table: StringTable) -> StringTable:
    return string_table


check_info["pfsense_status"] = LegacyCheckDefinition(
    name="pfsense_status",
    parse_function=parse_pfsense_status,
    detect=contains(".1.3.6.1.2.1.1.1.0", "pfsense"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.12325.1.200.1.1",
        oids=["1"],
    ),
    service_name="pfSense Status",
    discovery_function=discover_pfsense_status,
    check_function=check_pfsense_status,
)
