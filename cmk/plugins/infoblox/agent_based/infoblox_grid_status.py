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
from cmk.plugins.infoblox.lib import DETECT_INFOBLOX

# .1.3.6.1.4.1.7779.3.1.1.2.1.15.0 X.X.X.X --> IB-PLATFORMONE-MIB::ibGridMasterVIP.0
# .1.3.6.1.4.1.7779.3.1.1.2.1.16.0 ONLINE --> IB-PLATFORMONE-MIB::ibGridReplicationState.0


def parse_infoblox_grid_status(string_table: StringTable) -> StringTable | None:
    return string_table or None


snmp_section_infoblox_grid_status = SimpleSNMPSection(
    name="infoblox_grid_status",
    parse_function=parse_infoblox_grid_status,
    detect=DETECT_INFOBLOX,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.7779.3.1.1.2.1",
        oids=["15", "16"],
    ),
)


def discover_infoblox_grid_status(section: StringTable) -> DiscoveryResult:
    yield Service()


def check_infoblox_grid_status(section: StringTable) -> CheckResult:
    master_vip, status = section[0]
    status_readable = status.lower()

    yield Result(
        state=State.OK if status_readable == "online" else State.CRIT,
        summary=f"Status: {status_readable}, Master virtual IP: {master_vip}",
    )


check_plugin_infoblox_grid_status = CheckPlugin(
    name="infoblox_grid_status",
    service_name="Grid replication",
    discovery_function=discover_infoblox_grid_status,
    check_function=check_infoblox_grid_status,
)
