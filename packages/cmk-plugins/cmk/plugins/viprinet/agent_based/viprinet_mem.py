#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import NewType

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    render,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.viprinet.lib import DETECT_VIPRINET

MemoryUsedInBytes = NewType("MemoryUsedInBytes", int)


def parse_viprinet_mem(string_table: StringTable) -> MemoryUsedInBytes | None:
    match string_table:
        case [[str(value)]] if value.isdigit():
            return MemoryUsedInBytes(int(value))
        case _:
            return None


def discover_viprinet_mem(section: MemoryUsedInBytes) -> DiscoveryResult:
    yield Service()


def check_viprinet_mem(section: MemoryUsedInBytes) -> CheckResult:
    yield Result(state=State.OK, summary=f"Memory used: {render.bytes(section)}")


snmp_section_viprinet_mem = SimpleSNMPSection(
    name="viprinet_mem",
    detect=DETECT_VIPRINET,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.35424.1.2",
        oids=["2"],
    ),
    parse_function=parse_viprinet_mem,
)


check_plugin_viprinet_mem = CheckPlugin(
    name="viprinet_mem",
    service_name="Memory",
    discovery_function=discover_viprinet_mem,
    check_function=check_viprinet_mem,
)
