#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# F5OS rSeries hardware/software inventory
# MIB: F5-PLATFORM-STATS-MIB (enterprise .1.3.6.1.4.1.12276.1)

import re
from collections.abc import Sequence
from dataclasses import dataclass

from cmk.agent_based.v2 import (
    Attributes,
    InventoryPlugin,
    InventoryResult,
    OIDEnd,
    SNMPSection,
    SNMPTree,
    StringTable,
    TableRow,
)
from cmk.plugins.f5os_rseries.lib.detect import DETECT_F5OS_RSERIES
from cmk.plugins.f5os_rseries.lib.psu import F5OSPSU


def _optional_int(value: str) -> int | None:
    """Parse an optional inventory integer, tolerating a missing/non-numeric value.

    Inventory is descriptive rather than alerting, so a dropped field is preferable to
    failing the whole inventory. The monitoring checks instead convert their SNMP columns
    directly (``int``/``float``): per the F5-PLATFORM-STATS-MIB those columns are always
    populated with a number (a standby PSU reports a genuine ``0``, not an empty value), so
    an unreadable reading there is unexpected and is allowed to surface as a crash report
    rather than be silently coerced into a fabricated value.
    """
    try:
        return int(value)
    except TypeError, ValueError:
        return None


@dataclass(frozen=True)
class F5OSInventorySection:
    sysdescr: str
    model: str
    cpu_model: str
    cpu_cores_physical: int | None
    cpu_cores_logical: int | None
    disk_model: str
    disk_serial: str
    disk_capacity: str


def parse_f5os_rseries_inventory(
    string_table: Sequence[StringTable],
) -> F5OSInventorySection | None:
    if not string_table or not string_table[0]:
        return None

    sysdescr = string_table[0][0][0].strip("\0")

    model = ""
    if len(string_table) > 1 and string_table[1]:
        # row: [OIDEnd, platformModel]
        model = string_table[1][0][1].strip("\0")

    cpu_model = ""
    cpu_cores_physical = None
    cpu_cores_logical = None
    if len(string_table) > 2 and string_table[2]:
        # row: [OIDEnd, cpuPhysicalCores, cpuLogicalCPUs, cpuModel]
        row = string_table[2][0]
        cpu_cores_physical = _optional_int(row[1])
        cpu_cores_logical = _optional_int(row[2])
        cpu_model = row[3].strip("\0")

    disk_model = disk_serial = disk_capacity = ""
    if len(string_table) > 3 and string_table[3]:
        # row: [OIDEnd, diskModel, diskSerial, diskCapacity]
        row = string_table[3][0]
        disk_model = row[1].strip("\0")
        disk_serial = row[2].strip("\0")
        disk_capacity = row[3].strip("\0")

    return F5OSInventorySection(
        sysdescr=sysdescr,
        model=model,
        cpu_model=cpu_model,
        cpu_cores_physical=cpu_cores_physical,
        cpu_cores_logical=cpu_cores_logical,
        disk_model=disk_model,
        disk_serial=disk_serial,
        disk_capacity=disk_capacity,
    )


snmp_section_f5os_rseries_inventory = SNMPSection(
    name="f5os_rseries_inventory",
    parse_function=parse_f5os_rseries_inventory,
    detect=DETECT_F5OS_RSERIES,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.2.1.1",
            oids=["1.0"],  # sysDescr (scalar)
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.12276.1.2.1.8.1.1",
            oids=[
                OIDEnd(),  # row index (OctetString-encoded "platform")
                "2",  # platformModel (e.g. "r5800")
            ],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.12276.1.2.1.1.1.1",
            oids=[
                OIDEnd(),  # row index
                "4",  # cpuPhysicalCores
                "7",  # cpuLogicalCPUs
                "8",  # cpuModel
            ],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.12276.1.2.1.2.1.1",
            oids=[
                OIDEnd(),  # row index (OctetString-encoded "platform.nvme0n1")
                "3",  # nvmeDiskModel
                "6",  # nvmeDiskSerial
                "7",  # nvmeDiskCapacity
            ],
        ),
    ],
)


def _extract_f5os_version(sysdescr: str) -> str:
    m = re.search(r"version\s+([\d.\-]+)", sysdescr, re.IGNORECASE)
    return m.group(1) if m else ""


def inventory_f5os_rseries(
    section_f5os_rseries_inventory: F5OSInventorySection | None,
    section_f5os_rseries_psu: dict[str, F5OSPSU] | None,
) -> InventoryResult:
    if section_f5os_rseries_inventory is None:
        return

    inv = section_f5os_rseries_inventory

    yield Attributes(path=["hardware", "system"], inventory_attributes={"model": inv.model})

    f5os_version = _extract_f5os_version(inv.sysdescr)
    if f5os_version:
        yield Attributes(
            path=["software", "os"],
            inventory_attributes={"version": f5os_version},
        )

    if inv.cpu_model:
        cpu_attrs: dict[str, str | int] = {"model": inv.cpu_model}
        if inv.cpu_cores_physical is not None:
            cpu_attrs["cores"] = inv.cpu_cores_physical
        if inv.cpu_cores_logical is not None:
            cpu_attrs["threads"] = inv.cpu_cores_logical
        yield Attributes(path=["hardware", "cpu"], inventory_attributes=cpu_attrs)

    if inv.disk_model:
        yield Attributes(
            path=["hardware", "storage"],
            inventory_attributes={
                "model": inv.disk_model,
                "serial": inv.disk_serial,
                "capacity": inv.disk_capacity,
            },
        )

    if section_f5os_rseries_psu:
        for psu_name, psu in section_f5os_rseries_psu.items():
            if psu.serial or psu.model:
                yield TableRow(
                    path=["hardware", "components", "psus"],
                    key_columns={"name": psu_name},
                    inventory_columns={
                        "serial": psu.serial,
                        "model": psu.model,
                    },
                )


inventory_plugin_f5os_rseries = InventoryPlugin(
    name="f5os_rseries",
    sections=["f5os_rseries_inventory", "f5os_rseries_psu"],
    inventory_function=inventory_f5os_rseries,
)
