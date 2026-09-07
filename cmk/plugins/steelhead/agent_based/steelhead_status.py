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
from cmk.plugins.steelhead.lib import DETECT_STEELHEAD


def parse_steelhead_status(string_table: StringTable) -> StringTable:
    return string_table


snmp_section_steelhead_status = SimpleSNMPSection(
    name="steelhead_status",
    parse_function=parse_steelhead_status,
    detect=DETECT_STEELHEAD,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.17163.1.1.2",
        oids=["2", "3"],
    ),
)


def discover_steelhead_status(section: StringTable) -> DiscoveryResult:
    if len(section) == 1:
        yield Service()


def check_steelhead_status(section: StringTable) -> CheckResult:
    health, status = section[0]
    if health == "Healthy" and status == "running":
        yield Result(state=State.OK, summary="Healthy and running")
        return
    yield Result(state=State.CRIT, summary=f"Status is {health} and {status}")


check_plugin_steelhead_status = CheckPlugin(
    name="steelhead_status",
    service_name="Status",
    discovery_function=discover_steelhead_status,
    check_function=check_steelhead_status,
)
