#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum

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
from cmk.plugins.dell.lib import DETECT_IDRAC_POWEREDGE

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


class DiskState(Enum):
    UNKNOWN = "1"
    ONLINE = "2"
    FAILED = "3"
    DEGRADED = "4"

    @property
    def label(self) -> str:
        return self.name.lower()

    @property
    def state(self) -> State:
        match self:
            case DiskState.UNKNOWN:
                return State.WARN
            case DiskState.ONLINE:
                return State.OK
            case _:
                return State.CRIT


class RaidType(Enum):
    NONE = "1"
    RAID_0 = "2"
    RAID_1 = "3"
    RAID_5 = "4"
    RAID_6 = "5"
    RAID_10 = "6"
    RAID_50 = "7"
    RAID_60 = "8"
    CONCATENATED_RAID_1 = "9"

    @property
    def label(self) -> str:
        return self.name.title().replace("_", "-")


class ComponentState(Enum):
    OTHER = "1"
    UNKNOWN = "2"
    OK = "3"
    NON_CRITICAL = "4"
    CRITICAL = "5"
    NON_RECOVERABLE = "6"

    @property
    def label(self) -> str:
        return self.name.lower().replace("_", "-")

    @property
    def state(self) -> State:
        match self:
            case ComponentState.OTHER | ComponentState.OK:
                return State.OK
            case ComponentState.UNKNOWN | ComponentState.NON_CRITICAL:
                return State.WARN
            case _:
                return State.CRIT


@dataclass
class VirtualDisk:
    # base OID:      .1.3.6.1.4.1.674.10892.5.5.1.20.140.1.1
    index: int  # 1
    name: str  # 2
    disk_state: DiskState  # 4
    raid_type: RaidType  # 13
    component_state: ComponentState  # 20
    remaining_redundancy: int  # 34

    @property
    def item(self) -> str:
        return self.name if self.name else f"noname-{self.index}"


Section = Mapping[str, VirtualDisk]


def discover_dell_idrac_virtdisks(section: Section) -> DiscoveryResult:
    for item in section:
        yield Service(item=item)


def check_dell_idrac_virtdisks(item: str, section: Section) -> CheckResult:
    disk = section.get(item)
    if not disk:
        return

    yield Result(state=State.OK, summary=f"Raid level: {disk.raid_type.label}")
    yield Result(state=disk.disk_state.state, summary=f"Disk status: {disk.disk_state.label}")
    yield Result(
        state=disk.component_state.state,
        summary=f"Component status: {disk.component_state.label}",
    )
    yield Result(
        state=State.OK,
        summary=f"Remaining redundancy: {disk.remaining_redundancy} physical disk(s)",
    )


def parse_dell_idrac_virtdisks(string_table: StringTable) -> Section:
    return {
        disk.item: disk
        for disk in (
            VirtualDisk(
                index=int(row[0]),
                name=row[1],
                disk_state=DiskState(row[2]),
                raid_type=RaidType(row[3]),
                component_state=ComponentState(row[4]),
                remaining_redundancy=int(row[5]),
            )
            for row in string_table
        )
    }


snmp_section_dell_idrac_virtdisks = SimpleSNMPSection(
    name="dell_idrac_virtdisks",
    detect=DETECT_IDRAC_POWEREDGE,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.674.10892.5.5.1.20.140.1.1",
        oids=["1", "2", "4", "13", "20", "34"],
    ),
    parse_function=parse_dell_idrac_virtdisks,
)
check_plugin_dell_idrac_virtdisks = CheckPlugin(
    name="dell_idrac_virtdisks",
    service_name="Virtual Disk %s",
    discovery_function=discover_dell_idrac_virtdisks,
    check_function=check_dell_idrac_virtdisks,
)
