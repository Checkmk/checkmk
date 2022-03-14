#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Create block devices inventory from Linux device tree information
Sample agent output:

    <<<lnx_block_devices:sep(0):persist(1593783273)>>>
    |device|/sys/devices/pci0000:00/0000:00:1d.4/0000:3b:00.0/nvme/nvme0/nvme0n1|
    |size|1000215216|
    |uuid|ace42e00-955b-21fd-2ee4-ac0000000001|
    |device/address|0000:3b:00.0|
    |device/firmware_rev|80002111|
    |device/model|PC601 NVMe SK hynix 512GB               |
    |device/serial|AJ98N635810808T29   |
"""

from itertools import groupby
from typing import Mapping, Sequence

from .agent_based_api.v1 import register, TableRow
from .agent_based_api.v1.type_defs import InventoryResult, StringTable

Section = Sequence[Mapping[str, str]]


def _translate(name, value):
    """Translate dev-tree names and values to inventory item names and values
    Still unclear:
        "vendor": "Manufacturer" on Windows, but can also be "QEMU", "ATA"
        "bus":    "InterfaceType" on Windows
        "type":   "MediaType" on Wondows
        ".hardware.storage.disks:*.vendor": {"title": _("Vendor")},
        ".hardware.storage.disks:*.bus": {"title": _("Bus")},
        ".hardware.storage.disks:*.type": {"title": _("Type")},
    """
    stripped = str.strip(value)
    if stripped == "":
        return None
    if name == "device":
        return "fsnode", stripped
    if name == "uuid":  # or "wwid" or "nguid"
        # see https://lore.kernel.org/patchwork/patch/808637/
        return "signature", stripped
    if name == "size":
        return "size", int(stripped) * 512
    if name == "device/model":
        return "product", stripped
    if name == "device/serial":
        return "serial", stripped
    if name == "device/firmware_rev":
        return "firmware", stripped
    if name == "device/vendor":
        return "vendor", stripped
    return None


def _pairify(line):
    """Return a (key, value) tuple from a validly formatted @line `|key|value|`. If parsing or
    reformatting fails return None"""
    try:
        _, name, value, *_rest = line[0].split("|")
        return _translate(name, value)
    except ValueError:
        return None


def parse_lnx_block_devices(string_table: StringTable) -> Section:
    """Turn lines containing device names and attributes into a list of dicts
    containing those values for each device"""
    # translate list of encoded lines into list of key-value-pairs
    lines = (line for li in string_table for line in (_pairify(li),) if line)
    # create a list of chunks of key-value-pairs preceded by a `fsnode` entry
    it = iter([list(pairs) for _, pairs in groupby(lines, lambda pair: pair[0] == "fsnode")])
    # return a list of dicts created from the chunks
    return [dict((name, *attrs)) for (*_, name), attrs in zip(it, it)]


register.agent_section(
    name="lnx_block_devices",
    parse_function=parse_lnx_block_devices,
)


def inventory_lnx_block_devices(section: Section) -> InventoryResult:
    path = ["hardware", "storage", "disks"]
    for row in section:
        yield TableRow(
            path=path,
            key_columns={
                "fsnode": row["fsnode"],
            },
            inventory_columns={
                "firmware": row.get("firmware", ""),
                "product": row.get("product", ""),
                "serial": row.get("serial", ""),
                "signature": row.get("signature", ""),
                "size": row.get("size", ""),
            },
            status_columns={},
        )


register.inventory_plugin(
    name="lnx_block_devices",
    inventory_function=inventory_lnx_block_devices,
)
