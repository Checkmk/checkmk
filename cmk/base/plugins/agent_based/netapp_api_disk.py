#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Example output:
# <<<netapp_api_disk:sep(9)>>>
# disk 4E455441:50502020:56442D39:3030304D:422D465A:2D353230:38383633:32303037:00000000:00000000  used-space 9458679808   serial-number 88632007  raid-type pending vendor-id ..

from typing import Any, Dict, List, Mapping, Sequence

from .agent_based_api.v1 import register, render, TableRow
from .agent_based_api.v1.type_defs import InventoryResult, StringTable

Section = Sequence[Mapping[str, Any]]


def parse_netapp_api_disk(string_table: StringTable) -> Section:
    disks: List[Dict[str, Any]] = []
    for line in string_table:
        raw_disk = _parse_line(line)

        disk: Dict[str, Any] = {}

        serial = raw_disk.get("serial-number")

        disk_info = "Serial: %s" % serial
        if "physical-space" in raw_disk:
            disk_info += ", Size: %s" % render.bytes(int(raw_disk["physical-space"]))
            disk["capacity"] = int(raw_disk["physical-space"])

        disk["identifier"] = disk_info
        disk["type"] = False
        raid_type = raw_disk.get("raid-type")
        raid_state = raw_disk.get("raid-state")

        # need this for sorting out disks in the check function
        disk["raid-state"] = raid_state

        if raid_state == "broken":
            disk["state"] = "failed"
        elif disk.get("prefailed", "false") not in ["false", "None"]:
            disk["state"] = "prefailed"
        elif raid_state == "spare":
            disk["state"] = "spare"
        else:
            disk["state"] = "ok"

        if raid_type in ["parity", "dparity"]:
            disk["type"] = "parity"
        elif raid_type == "data":
            disk["type"] = "data"

        # For HW/SW inventory
        disk["signature"] = raw_disk["disk"]
        disk["serial"] = serial
        disk["vendor"] = raw_disk.get("vendor-id")
        bay = raw_disk.get("bay")
        disk["bay"] = None if bay == "?" else bay

        disks.append(disk)
    return disks


def _parse_line(line: Sequence[str]) -> Mapping[str, str]:
    parsed_line: Dict[str, str] = {}
    for word in line:
        try:
            key, value = word.split(" ", 1)
        except ValueError:
            continue
        parsed_line[key] = value
    return parsed_line


register.agent_section(
    name="netapp_api_disk",
    parse_function=parse_netapp_api_disk,
)


def inventory_netapp_api_disk(section: Section) -> InventoryResult:
    for disk in sorted(section, key=lambda d: d.get("signature", "")):
        yield TableRow(
            path=["hardware", "storage", "disks"],
            key_columns={
                "signature": disk["signature"],
            },
            inventory_columns={
                "serial": disk["serial"],
                "vendor": disk["vendor"],
                "bay": disk["bay"],
            },
            status_columns={},
        )


register.inventory_plugin(
    name="netapp_api_disk",
    inventory_function=inventory_netapp_api_disk,
)
