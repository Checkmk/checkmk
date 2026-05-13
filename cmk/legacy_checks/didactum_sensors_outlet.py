#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    SimpleSNMPSection,
    SNMPTree,
)
from cmk.plugins.didactum.lib import (
    check_didactum_sensor_status,
    DETECT_DIDACTUM,
    discover_didactum_sensors,
    parse_didactum_sensors,
    Section,
)

snmp_section_didactum_sensors_outlet = SimpleSNMPSection(
    name="didactum_sensors_outlet",
    detect=DETECT_DIDACTUM,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.46501.5.3.1",
        oids=["4", "5", "6", "7"],
    ),
    parse_function=parse_didactum_sensors,
)


def discover_didactum_sensors_outlet_relay(section: Section) -> DiscoveryResult:
    yield from discover_didactum_sensors(section, "relay")


def check_didactum_sensors_outlet_relay(item: str, section: Section) -> CheckResult:
    yield from check_didactum_sensor_status(item, section, "relay")


check_plugin_didactum_sensors_outlet = CheckPlugin(
    name="didactum_sensors_outlet",
    service_name="Relay %s",
    discovery_function=discover_didactum_sensors_outlet_relay,
    check_function=check_didactum_sensors_outlet_relay,
)
