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
from cmk.plugins.lib.dell import DETECT_IDRAC_POWEREDGE

# .1.3.6.1.4.1.674.10892.5.5.1.20.140.1.1.2.1 System --> IDRAC-MIB::virtualDiskName.1
# .1.3.6.1.4.1.674.10892.5.5.1.20.140.1.1.2.2 Oracle --> IDRAC-MIB::virtualDiskName.2
# .1.3.6.1.4.1.674.10892.5.5.1.20.140.1.1.2.3 Backup --> IDRAC-MIB::virtualDiskName.3
# .1.3.6.1.4.1.674.10892.5.5.1.20.140.1.1.4.1 2 --> IDRAC-MIB::virtualDiskState.1
# .1.3.6.1.4.1.674.10892.5.5.1.20.140.1.1.4.2 2 --> IDRAC-MIB::virtualDiskState.2
# .1.3.6.1.4.1.674.10892.5.5.1.20.140.1.1.4.3 2 --> IDRAC-MIB::virtualDiskState.3
# .1.3.6.1.4.1.674.10892.5.5.1.20.140.1.1.20.1 3 --> IDRAC-MIB::virtualDiskComponentStatus.1
# .1.3.6.1.4.1.674.10892.5.5.1.20.140.1.1.20.2 3 --> IDRAC-MIB::virtualDiskComponentStatus.2
# .1.3.6.1.4.1.674.10892.5.5.1.20.140.1.1.20.3 3 --> IDRAC-MIB::virtualDiskComponentStatus.3
# .1.3.6.1.4.1.674.10892.5.5.1.20.140.1.1.34.1 1 --> IDRAC-MIB::virtualDiskRemainingRedundancy.1
# .1.3.6.1.4.1.674.10892.5.5.1.20.140.1.1.34.2 1 --> IDRAC-MIB::virtualDiskRemainingRedundancy.2
# .1.3.6.1.4.1.674.10892.5.5.1.20.140.1.1.34.3 1 --> IDRAC-MIB::virtualDiskRemainingRedundancy.3


def inventory_dell_idrac_virtdisks(section: StringTable) -> DiscoveryResult:
    yield from [Service(item=line[0]) for line in section]


def check_dell_idrac_virtdisks(item: str, section: StringTable) -> CheckResult:
    map_states = {
        "disk": {
            "1": (State.WARN, "unknown"),
            "2": (State.OK, "online"),
            "3": (State.CRIT, "failed"),
            "4": (State.CRIT, "degraded"),
        },
        "component": {
            "1": (State.OK, "other"),
            "2": (State.WARN, "unknown"),
            "3": (State.OK, "OK"),
            "4": (State.WARN, "non-critical"),
            "5": (State.CRIT, "critical"),
            "6": (State.CRIT, "non-recoverable"),
        },
    }
    map_raidlevel = {
        "1": "none",
        "2": "Raid-0",
        "3": "Raid-1",
        "4": "Raid-5",
        "5": "Raid-6",
        "6": "Raid-10",
        "7": "Raid-50",
        "8": "Raid-60",
    }

    for name, disk_state, raid_level, component_state, redundancy in section:
        if item == name:
            yield Result(state=State.OK, summary="Raid level: %s" % map_raidlevel[raid_level])

            for what, what_key in [(disk_state, "Disk"), (component_state, "Component")]:
                state, state_readable = map_states[what_key.lower()][what]
                yield Result(state=state, summary=f"{what_key} status: {state_readable}")

            yield Result(
                state=State.OK, summary="Remaining redundancy: %s physical disk(s)" % redundancy
            )


def parse_dell_idrac_virtdisks(string_table: StringTable) -> StringTable:
    return string_table


snmp_section_dell_idrac_virtdisks = SimpleSNMPSection(
    name="dell_idrac_virtdisks",
    detect=DETECT_IDRAC_POWEREDGE,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.674.10892.5.5.1.20.140.1.1",
        oids=["2", "4", "13", "20", "34"],
    ),
    parse_function=parse_dell_idrac_virtdisks,
)
check_plugin_dell_idrac_virtdisks = CheckPlugin(
    name="dell_idrac_virtdisks",
    service_name="Virtual Disk %s",
    discovery_function=inventory_dell_idrac_virtdisks,
    check_function=check_dell_idrac_virtdisks,
)
