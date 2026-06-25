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
from cmk.plugins.ups.lib import check_ups_out_voltage, DETECT_UPS_GENERIC


def parse_ups_out_voltage(string_table: StringTable) -> StringTable:
    return string_table


def discover_ups_out_voltage(section: StringTable) -> DiscoveryResult:
    yield from (Service(item=item) for item, value, *_rest in section if int(value) > 0)


snmp_section_ups_out_voltage = SimpleSNMPSection(
    name="ups_out_voltage",
    detect=DETECT_UPS_GENERIC,
    fetch=SNMPTree(
        base=".1.3.6.1.2.1.33.1.4.4.1",
        oids=[OIDEnd(), "2"],
    ),
    parse_function=parse_ups_out_voltage,
)


check_plugin_ups_out_voltage = CheckPlugin(
    name="ups_out_voltage",
    service_name="OUT voltage phase %s",
    discovery_function=discover_ups_out_voltage,
    check_function=check_ups_out_voltage,
    check_ruleset_name="evolt",
    check_default_parameters={
        "levels_lower": (210.0, 180.0),
    },
)
