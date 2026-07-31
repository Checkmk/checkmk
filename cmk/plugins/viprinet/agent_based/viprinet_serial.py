#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.viprinet.lib import DETECT_VIPRINET


def discover_viprinet_serial(section: StringTable) -> DiscoveryResult:
    if section:
        yield Service()


def check_viprinet_serial(section: StringTable) -> CheckResult:
    yield Result(state=State.OK, summary=section[0][0])


def parse_viprinet_serial(string_table: StringTable) -> StringTable:
    return string_table


snmp_section_viprinet_serial = SimpleSNMPSection(
    name="viprinet_serial",
    detect=DETECT_VIPRINET,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.35424.1.1",
        oids=["2"],
    ),
    parse_function=parse_viprinet_serial,
)


check_plugin_viprinet_serial = CheckPlugin(
    name="viprinet_serial",
    service_name="Serial Number",
    discovery_function=discover_viprinet_serial,
    check_function=check_viprinet_serial,
)
