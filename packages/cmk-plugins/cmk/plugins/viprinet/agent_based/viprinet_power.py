#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import NewType

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

PowerStatus = NewType("PowerStatus", str)


def parse_viprinet_power(string_table: StringTable) -> PowerStatus | None:
    match string_table:
        case [[str(value)]]:
            return PowerStatus(value)
        case _:
            return None


def discover_viprinet_power(section: PowerStatus) -> DiscoveryResult:
    yield Service()


def check_viprinet_power(section: PowerStatus) -> CheckResult:
    match section:
        case "0":
            yield Result(state=State.OK, summary="no failure")
        case "1":
            yield Result(state=State.OK, summary="a single PSU is out of order")
        case _:
            yield Result(state=State.UNKNOWN, summary="Invalid power status")


snmp_section_viprinet_power = SimpleSNMPSection(
    name="viprinet_power",
    detect=DETECT_VIPRINET,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.35424.1.2",
        oids=["5"],
    ),
    parse_function=parse_viprinet_power,
)


check_plugin_viprinet_power = CheckPlugin(
    name="viprinet_power",
    service_name="Power-Supply",
    discovery_function=discover_viprinet_power,
    check_function=check_viprinet_power,
)
