#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


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
from cmk.plugins.lib.dell import DETECT_IDRAC_POWEREDGE

# .1.3.6.1.4.1.674.10892.5.5.1.20.130.4.1.2.1 Physical Disk 0:1:0 --> IDRAC-MIB::physicalDiskName.1
# .1.3.6.1.4.1.674.10892.5.5.1.20.130.4.1.2.2 Physical Disk 0:1:1 --> IDRAC-MIB::physicalDiskName.2
# .1.3.6.1.4.1.674.10892.5.5.1.20.130.4.1.4.1 8 --> IDRAC-MIB::physicalDiskState.1
# .1.3.6.1.4.1.674.10892.5.5.1.20.130.4.1.4.2 8 --> IDRAC-MIB::physicalDiskState.2
# .1.3.6.1.4.1.674.10892.5.5.1.20.130.4.1.11.1 1144064 --> IDRAC-MIB::physicalDiskCapacityInMB.1
# .1.3.6.1.4.1.674.10892.5.5.1.20.130.4.1.11.2 1144064 --> IDRAC-MIB::physicalDiskCapacityInMB.2
# .1.3.6.1.4.1.674.10892.5.5.1.20.130.4.1.22.1 1 --> IDRAC-MIB::physicalDiskSpareState.1
# .1.3.6.1.4.1.674.10892.5.5.1.20.130.4.1.22.2 1 --> IDRAC-MIB::physicalDiskSpareState.2
# .1.3.6.1.4.1.674.10892.5.5.1.20.130.4.1.24.1 3 --> IDRAC-MIB::physicalDiskComponentStatus.1
# .1.3.6.1.4.1.674.10892.5.5.1.20.130.4.1.24.2 3 --> IDRAC-MIB::physicalDiskComponentStatus.2
# .1.3.6.1.4.1.674.10892.5.5.1.20.130.4.1.31.1 0 --> IDRAC-MIB::physicalDiskSmartAlertIndication.1
# .1.3.6.1.4.1.674.10892.5.5.1.20.130.4.1.31.2 0 --> IDRAC-MIB::physicalDiskSmartAlertIndication.2
# .1.3.6.1.4.1.674.10892.5.5.1.20.130.4.1.55.1 Disk 0 in Backplane 1 of Integrated RAID Controller 1 --> IDRAC-MIB::physicalDiskDisplayName.1
# .1.3.6.1.4.1.674.10892.5.5.1.20.130.4.1.55.2 Disk 1 in Backplane 1 of Integrated RAID Controller 1 --> IDRAC-MIB::physicalDiskDisplayName.2


def inventory_dell_idrac_disks(section: StringTable) -> DiscoveryResult:
    inventory = []
    for line in section:
        inventory.append((line[0], None))
    yield from [Service(item=item, parameters=parameters) for (item, parameters) in inventory]


def check_dell_idrac_disks(item: str, section: StringTable) -> CheckResult:
    map_states = {
        "disk_states": {
            "1": (State.WARN, "unknown"),
            "2": (State.OK, "ready"),
            "3": (State.OK, "online"),
            "4": (State.WARN, "foreign"),
            "5": (State.CRIT, "offline"),
            "6": (State.CRIT, "blocked"),
            "7": (State.CRIT, "failed"),
            "8": (State.OK, "non-raid"),
            "9": (State.OK, "removed"),
        },
        "component_states": {
            "1": (State.OK, "other"),
            "2": (State.WARN, "unknown"),
            "3": (State.OK, "OK"),
            "4": (State.OK, "non-critical"),
            "5": (State.CRIT, "critical"),
            "6": (State.WARN, "non-recoverable"),
        },
        "diskpower_states": {
            "1": (State.OK, "no-operation"),
            "2": (State.WARN, "REBUILDING"),
            "3": (State.WARN, "data-erased"),
            "4": (State.WARN, "COPY-BACK"),
        },
    }

    map_spare_state_info = {
        "1": "not a spare",
        "2": "dedicated hotspare",
        "3": "global hotspare",
    }

    for (
        disk_name,
        disk_state,
        capacity_MB,
        spare_state,
        component_state,
        smart_alert,
        diskpower_state,
        display_name,
    ) in section:
        if disk_name == item:
            yield Result(
                state=State.OK,
                summary=f"[{display_name}] Size: {render.disksize(int(capacity_MB) * 1024 * 1024)}",
            )

            for what, what_key, what_text in [
                (disk_state, "disk_states", "Disk state"),
                (component_state, "component_states", "Component state"),
            ]:
                state, state_readable = map_states[what_key][what]
                yield Result(state=state, summary=f"{what_text}: {state_readable}")

            if smart_alert != "0":
                yield Result(state=State.CRIT, summary="Smart alert on disk")

            if spare_state != "1":
                yield Result(state=State.OK, summary=map_spare_state_info[spare_state])

            if diskpower_state != "1":
                state, state_readable = map_states["diskpower_states"][diskpower_state]
                yield Result(state=state, summary="%s" % (state_readable))


def parse_dell_idrac_disks(string_table: StringTable) -> StringTable:
    return string_table


snmp_section_dell_idrac_disks = SimpleSNMPSection(
    name="dell_idrac_disks",
    detect=DETECT_IDRAC_POWEREDGE,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.674.10892.5.5.1.20.130.4.1",
        oids=["2", "4", "11", "22", "24", "31", "50", "55"],
    ),
    parse_function=parse_dell_idrac_disks,
)
check_plugin_dell_idrac_disks = CheckPlugin(
    name="dell_idrac_disks",
    service_name="Disk %s",
    discovery_function=inventory_dell_idrac_disks,
    check_function=check_dell_idrac_disks,
)
