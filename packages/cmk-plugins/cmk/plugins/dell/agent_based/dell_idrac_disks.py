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
    render,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.dell.lib import DETECT_IDRAC_POWEREDGE

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


class DiskState(Enum):
    UNKNOWN = "1"
    READY = "2"
    ONLINE = "3"
    FOREIGN = "4"
    OFFLINE = "5"
    BLOCKED = "6"
    FAILED = "7"
    NON_RAID = "8"
    REMOVED = "9"
    READ_ONLY = "10"

    @property
    def label(self) -> str:
        return self.name.lower().replace("_", "-")

    @property
    def state(self) -> State:
        match self:
            case (
                DiskState.READY
                | DiskState.ONLINE
                | DiskState.NON_RAID
                | DiskState.REMOVED
                | DiskState.READ_ONLY
            ):
                return State.OK
            case DiskState.UNKNOWN | DiskState.FOREIGN:
                return State.WARN
            case _:
                return State.CRIT


class SpareState(Enum):
    NOT_A_SPARE = "1"
    DEDICATED_HOT_SPARE = "2"
    GLOBAL_HOT_SPARE = "3"

    @property
    def label(self) -> str:
        return self.name.lower().replace("_", " ")


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
            case ComponentState.OTHER | ComponentState.OK | ComponentState.NON_CRITICAL:
                return State.OK
            case ComponentState.UNKNOWN | ComponentState.NON_RECOVERABLE:
                return State.WARN
            case _:
                return State.CRIT


class OperationState(Enum):
    NOT_APPLICABLE = "1"
    REBUILD = "2"
    CLEAR = "3"
    COPYBACK = "4"

    @property
    def label(self) -> str:
        return self.name.lower().replace("_", "-")

    @property
    def state(self) -> State:
        if self is OperationState.NOT_APPLICABLE:
            return State.OK
        return State.WARN


@dataclass
class Disk:
    index: int  # .1
    name: str  # .2
    disk_state: DiskState  # .4
    capacity_MB: int  # .11
    spare_state: SpareState  # .22
    component_state: ComponentState  # .24
    smart_alert: bool  # .31
    operation_state: OperationState  # .50
    display_name: str  # .55

    @property
    def item(self) -> str:
        return self.name if self.name else f"noname-{self.index}"


Section = Mapping[str, Disk]


def discover_dell_idrac_disks(section: Section) -> DiscoveryResult:
    for item in section:
        yield Service(item=item)


def check_dell_idrac_disks(item: str, section: Section) -> CheckResult:
    disk = section.get(item)
    if not disk:
        return

    yield Result(
        state=State.OK,
        summary=f"[{disk.display_name}] Size: {render.disksize(disk.capacity_MB * 1024 * 1024)}",
    )
    yield Result(state=disk.disk_state.state, summary=f"Disk state: {disk.disk_state.label}")
    yield Result(
        state=disk.component_state.state,
        summary=f"Component state: {disk.component_state.label}",
    )
    if disk.smart_alert:
        yield Result(state=State.CRIT, summary="Smart alert on disk")
    yield Result(state=State.OK, summary=f"Spare state: {disk.spare_state.label}")
    yield Result(
        state=disk.operation_state.state,
        summary=f"Operation state: {disk.operation_state.label}",
    )


def parse_dell_idrac_disks(string_table: StringTable) -> Section:
    return {
        disk.item: disk
        for disk in (
            Disk(
                index=int(row[0]),
                name=row[1],
                disk_state=DiskState(row[2]),
                capacity_MB=int(row[3]),
                spare_state=SpareState(row[4]),
                component_state=ComponentState(row[5]),
                smart_alert=row[6] == "1",
                operation_state=OperationState(row[7]),
                display_name=row[8],
            )
            for row in string_table
        )
    }


snmp_section_dell_idrac_disks = SimpleSNMPSection(
    name="dell_idrac_disks",
    detect=DETECT_IDRAC_POWEREDGE,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.674.10892.5.5.1.20.130.4.1",
        oids=["1", "2", "4", "11", "22", "24", "31", "50", "55"],
    ),
    parse_function=parse_dell_idrac_disks,
)
check_plugin_dell_idrac_disks = CheckPlugin(
    name="dell_idrac_disks",
    service_name="Disk %s",
    discovery_function=discover_dell_idrac_disks,
    check_function=check_dell_idrac_disks,
)
