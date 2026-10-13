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

# .1.3.6.1.4.1.7779.3.1.1.2.1.2.1.1.X.X.X.X.X X.X.X.X --> IB-PLATFORMONE-MIB::ibNodeIPAddress."11.112.133.14"
# .1.3.6.1.4.1.7779.3.1.1.2.1.2.1.1.X.X.X.X.X X.X.X.X --> IB-PLATFORMONE-MIB::ibNodeIPAddress."11.112.133.17"
# .1.3.6.1.4.1.7779.3.1.1.2.1.2.1.2.X.X.X.X.X Online --> IB-PLATFORMONE-MIB::ibNodeReplicationStatus."11.112.133.14"
# .1.3.6.1.4.1.7779.3.1.1.2.1.2.1.2.X.X.X.X.X Online --> IB-PLATFORMONE-MIB::ibNodeReplicationStatus."11.112.133.17"
# .1.3.6.1.4.1.7779.3.1.1.2.1.2.1.3.X.X.X.X.X 0 --> IB-PLATFORMONE-MIB::ibNodeQueueFromMaster."11.112.133.14"
# .1.3.6.1.4.1.7779.3.1.1.2.1.2.1.3.X.X.X.X.X 0 --> IB-PLATFORMONE-MIB::ibNodeQueueFromMaster."11.112.133.17"
# .1.3.6.1.4.1.7779.3.1.1.2.1.2.1.4.X.X.X.X.X 2016/04/13 14:15:51 --> IB-PLATFORMONE-MIB::ibNodeLastRepTimeFromMaster."11.112.133.14"
# .1.3.6.1.4.1.7779.3.1.1.2.1.2.1.4.X.X.X.X.X 2016/04/13 14:15:51 --> IB-PLATFORMONE-MIB::ibNodeLastRepTimeFromMaster."11.112.133.17"
# .1.3.6.1.4.1.7779.3.1.1.2.1.2.1.5.X.X.X.X.X 0 --> IB-PLATFORMONE-MIB::ibNodeQueueToMaster."11.112.133.14"
# .1.3.6.1.4.1.7779.3.1.1.2.1.2.1.5.X.X.X.X.X 0 --> IB-PLATFORMONE-MIB::ibNodeQueueToMaster."11.112.133.17"
# .1.3.6.1.4.1.7779.3.1.1.2.1.2.1.6.X.X.X.X.X 2016/04/13 14:12:59 --> IB-PLATFORMONE-MIB::ibNodeLastRepTimeToMaster."11.112.133.14"
# .1.3.6.1.4.1.7779.3.1.1.2.1.2.1.6.X.X.X.X.X 2016/04/13 14:15:51 --> IB-PLATFORMONE-MIB::ibNodeLastRepTimeToMaster."11.112.133.17"


def parse_infoblox_replication_status(string_table: StringTable) -> StringTable:
    return string_table


snmp_section_infoblox_replication_status = SimpleSNMPSection(
    name="infoblox_replication_status",
    parse_function=parse_infoblox_replication_status,
    detect=DETECT_INFOBLOX,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.7779.3.1.1.2.1.2.1",
        oids=["1", "2", "3", "4", "5", "6"],
    ),
)


def discover_infoblox_replication_status(section: StringTable) -> DiscoveryResult:
    for line in section:
        yield Service(item=line[0])


def check_infoblox_replication_status(item: str, section: StringTable) -> CheckResult:
    for (
        ip_addr,
        status,
        queue_from_master,
        time_from_master,
        queue_to_master,
        time_to_master,
    ) in section:
        if ip_addr == item:
            status_readable = status.lower()

            yield Result(
                state=State.OK if status_readable == "online" else State.CRIT,
                summary=(
                    f"Status: {status_readable}, "
                    f"Queue from master: {queue_from_master} ({time_from_master}), "
                    f"Queue to master: {queue_to_master} ({time_to_master})"
                ),
            )
            return


check_plugin_infoblox_replication_status = CheckPlugin(
    name="infoblox_replication_status",
    service_name="Replication %s",
    discovery_function=discover_infoblox_replication_status,
    check_function=check_infoblox_replication_status,
)
