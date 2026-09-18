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
from cmk.plugins.cisco.lib_ucs import DETECT

# comNET GmbH, Fabian Binder - 2018-05-30

# .1.3.6.1.4.1.9.9.719.1.9.35.1.9   cucsComputeRackUnitAvailableMemory


def discover_cisco_ucs_mem_total(section: StringTable) -> DiscoveryResult:  # noqa: ARG001
    yield Service()


def check_cisco_ucs_mem_total(section: StringTable) -> CheckResult:
    total_memory = section[0][0]
    yield Result(state=State.OK, summary=f"Total Memory: {total_memory} MB")


def parse_cisco_ucs_mem_total(string_table: StringTable) -> StringTable | None:
    return string_table or None


snmp_section_cisco_ucs_mem_total = SimpleSNMPSection(
    name="cisco_ucs_mem_total",
    detect=DETECT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.9.9.719.1.9.35.1",
        oids=["9"],
    ),
    parse_function=parse_cisco_ucs_mem_total,
)


check_plugin_cisco_ucs_mem_total = CheckPlugin(
    name="cisco_ucs_mem_total",
    service_name="Memory total",
    discovery_function=discover_cisco_ucs_mem_total,
    check_function=check_cisco_ucs_mem_total,
)
