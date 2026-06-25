#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.v2 import (
    CheckPlugin,
    DiscoveryResult,
    OIDEnd,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    StringTable,
)
from cmk.plugins.ups.lib import check_ups_in_voltage, DETECT_UPS_GENERIC


def parse_ups_in_voltage(string_table: StringTable) -> StringTable:
    return string_table


def discover_ups_in_voltage(section: StringTable) -> DiscoveryResult:
    yield from (Service(item=item) for item, value, *_rest in section if int(value) > 0)


snmp_section_ups_in_voltage = SimpleSNMPSection(
    name="ups_in_voltage",
    detect=DETECT_UPS_GENERIC,
    fetch=SNMPTree(
        base=".1.3.6.1.2.1.33.1.3.3.1",
        oids=[OIDEnd(), "3"],
    ),
    parse_function=parse_ups_in_voltage,
)


check_plugin_ups_in_voltage = CheckPlugin(
    name="ups_in_voltage",
    service_name="IN voltage phase %s",
    discovery_function=discover_ups_in_voltage,
    check_function=check_ups_in_voltage,
    check_ruleset_name="evolt",
    check_default_parameters={
        "levels_lower": (210.0, 180.0),
    },
)
