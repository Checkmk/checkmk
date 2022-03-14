#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Dict, Mapping, NamedTuple

from .agent_based_api.v1 import register, Result, Service, SNMPTree, State, TableRow
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, InventoryResult, StringTable
from .utils.hp_proliant import DETECT

_MAP_CONDITION = {
    "0": "n/a",
    "1": "other",
    "2": "ok",
    "3": "degraded",
    "4": "failed",
}

_MAP_STATUS = {
    "1": "other",
    "2": "ok",
    "3": "failed",
    "4": "predictive failure",
    "5": "erasing",
    "6": "erase done",
    "7": "erase queued",
    "8": "SSD wear out",
    "9": "not authenticated",
}

_MAP_SMART_STATUS = {
    "1": "other",
    "2": "ok",
    "3": "replace drive",
    "4": "replace drive SSD wear out",
}
_MAP_TYPES = {
    "1": "other",
    "2": "parallel SCSI",
    "3": "SATA",
    "4": "SAS",
}


class PhysicalDrive(NamedTuple):
    controller_index: str
    drive_index: str
    bay: str
    status: str
    ref_hours: str
    size: int
    condition: str
    bus_number: str
    smart_status: str
    model: str
    serial: str
    drive_type: str
    firmware_revision: str


Section = Mapping[str, PhysicalDrive]


def parse_hp_proliant_da_phydrv(string_table: StringTable) -> Section:
    return {
        "%s/%s"
        % (cntlr_index, index): PhysicalDrive(
            controller_index=cntlr_index,
            drive_index=index,
            bay=bay,
            status=_map(_MAP_STATUS, status),
            ref_hours=ref_hours,
            size=int(size) * 1024**2,
            condition=_map(_MAP_CONDITION, condition),
            bus_number=bus_number,
            smart_status=_map(_MAP_SMART_STATUS, smart_status),
            model=model,
            serial=serial,
            drive_type=_map(_MAP_TYPES, ty),
            firmware_revision=fw,
        )
        for (
            cntlr_index,
            index,
            bay,
            status,
            ref_hours,
            size,
            condition,
            bus_number,
            smart_status,
            model,
            serial,
            ty,
            fw,
        ) in string_table
    }


register.snmp_section(
    name="hp_proliant_da_phydrv",
    parse_function=parse_hp_proliant_da_phydrv,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.232.3.2.5.1.1",
        oids=[
            "1",  # CPQIDA-MIB::cpqDaPhyDrvCntlrIndex
            "2",  # CPQIDA-MIB::cpqDaPhyDrvIndex
            "5",  # CPQIDA-MIB::cpqDaPhyDrvBay
            "6",  # CPQIDA-MIB::cpqDaPhyDrvStatus
            "9",  # CPQIDA-MIB::cpqDaPhyDrvRefHours
            "45",  # CPQIDA-MIB::cpqDaPhyDrvSize
            "37",  # CPQIDA-MIB::cpqDaPhyDrvCondition
            "50",  # CPQIDA-MIB::cpqDaPhyDrvBusNumber
            "57",  # CPQIDA-MIB::cpqDaPhyDrvSmartStatus
            "3",  # CPQIDA-MIB::cpqDaPhyDrvModel
            "51",  # CPQIDA-MIB::cpqDaPhyDrvSerialNum
            "60",  # CPQIDA-MIB::pqDaPhyDrvType
            "4",  # CPQIDA-MIB::cpqDaPhyDrvFWRev
        ],
    ),
    detect=DETECT,
)


def _map(mapping: Dict[str, str], value: str) -> str:
    return mapping.get(value, "unknown(%s)" % value)


def discover_hp_proliant_da_phydrv(section: Section) -> DiscoveryResult:
    for physical_drive_name in section:
        yield Service(item=physical_drive_name)


def check_hp_proliant_da_phydrv(item, section: Section) -> CheckResult:
    if (physical_drive := section.get(item)) is None:
        return

    if physical_drive.condition == "other":
        state = State.UNKNOWN
    elif physical_drive.condition == "ok":
        state = State.OK
    elif physical_drive.condition == "degraded":
        state = State.CRIT
    elif physical_drive.condition == "failed":
        state = State.CRIT
    else:
        state = State.UNKNOWN

    yield Result(
        state=state,
        summary=(
            "Bay: %s, Bus number: %s, Status: %s, Smart status: %s, Ref hours: %s, Size: %sMB,"
            " Condition: %s"
            % (
                physical_drive.bay,
                physical_drive.bus_number,
                physical_drive.status,
                physical_drive.smart_status,
                physical_drive.ref_hours,
                physical_drive.size,
                physical_drive.condition,
            )
        ),
    )


register.check_plugin(
    name="hp_proliant_da_phydrv",
    service_name="HW Phydrv %s",
    discovery_function=discover_hp_proliant_da_phydrv,
    check_function=check_hp_proliant_da_phydrv,
)


def inventory_hp_proliant_da_phydrv(section: Section) -> InventoryResult:
    path = ["hardware", "storage", "disks"]
    for physical_drive in section.values():
        yield TableRow(
            path=path,
            key_columns={
                "controller": physical_drive.controller_index,
                # TODO In the legacy inventory plugin the 'drive_index' is not used
                # but in the related check, the item consists of 'controller_index/drive_index'.
                # Fix this one day.
                # "index": physical_drive.drive_index,
            },
            inventory_columns={
                "bus": physical_drive.bus_number,
                "serial": physical_drive.serial,
                "size": physical_drive.size,
                "type": physical_drive.drive_type,
                "bay": physical_drive.bay,
                "model": physical_drive.model,
                "firmware": physical_drive.firmware_revision,
            },
            status_columns={},
        )


register.inventory_plugin(
    name="hp_proliant_da_phydrv",
    inventory_function=inventory_hp_proliant_da_phydrv,
)
