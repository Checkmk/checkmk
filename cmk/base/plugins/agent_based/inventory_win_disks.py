#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Example output:
# <<<win_disks:sep(58)>>>
# DeviceID                    : \\.\PHYSICALDRIVE0
# Partitions                  : 2
# InterfaceType               : IDE
# Size                        : 32210196480
# Caption                     : VBOX HARDDISK ATA Device
# Description                 : Laufwerk
# Manufacturer                : (Standardlaufwerke)
# MediaType                   : Fixed hard disk media
# Model                       : VBOX HARDDISK ATA Device
# Name                        : \\.\PHYSICALDRIVE0
# SerialNumber                : 42566539323537333930652d3836636263352065

# CapabilityDescriptions      : {Random Access, Supports Writing}
# BytesPerSector              : 512
# Index                       : 0
# FirmwareRevision            : 1.0
# MediaLoaded                 : True
# Status                      : OK
# SectorsPerTrack             : 63
# TotalCylinders              : 3916
# TotalHeads                  : 255
# TotalSectors                : 62910540
# TotalTracks                 : 998580
# TracksPerCylinder           : 255
# Capabilities                : {3, 4}
# Signature                   : 645875120
# SCSIBus                     : 0
# SCSILogicalUnit             : 0
# SCSIPort                    : 2
# SCSITargetId                : 0

from typing import Any, Dict, List, Mapping, Sequence

from .agent_based_api.v1 import register, TableRow
from .agent_based_api.v1.type_defs import InventoryResult, StringTable

Section = Sequence[Mapping[str, Any]]


def parse_win_disks(string_table: StringTable) -> Section:  # pylint: disable=too-many-branches
    disks: List[Mapping[str, Any]] = []
    array: Dict[str, Any] = {}
    first_varname = None

    for line in string_table:
        if len(line) < 2:
            continue

        stripped_line = [w.strip() for w in line]
        varname = stripped_line[0]
        value = ":".join(stripped_line[1:])

        if first_varname and varname == first_varname:
            # Looks like we have a new instance
            disks.append(array)
            array = {}

        if not first_varname:
            first_varname = varname

        if varname == "Manufacturer":
            array["vendor"] = value

        elif varname == "InterfaceType":
            array["bus"] = value

        elif varname == "Model":
            array["product"] = value

        elif varname == "Name":
            array["fsnode"] = value

        elif varname == "SerialNumber":
            array["serial"] = value

        elif varname == "Size" and value != "":
            array["size"] = int(value)

        elif varname == "MediaType" and value != "":
            array["type"] = value

        elif varname == "Signature":
            if value != "":
                array["signature"] = int(value)
            else:
                array["signature"] = 0

        array["local"] = True

    # Append the last array
    if array:
        disks.append(array)

    return disks


register.agent_section(
    name="win_disks",
    parse_function=parse_win_disks,
)


def inventory_win_disks(section: Section) -> InventoryResult:
    path = ["hardware", "storage", "disks"]
    for disk in section:
        if "fsnode" in disk:
            yield TableRow(
                path=path,
                key_columns={
                    "fsnode": disk["fsnode"],
                },
                inventory_columns={
                    "signature": disk.get("signature"),
                    "vendor": disk.get("vendor"),
                    "local": disk.get("local"),
                    "bus": disk.get("bus"),
                    "product": disk.get("product"),
                    "serial": disk.get("serial"),
                    "size": disk.get("size"),
                    "type": disk.get("type"),
                },
                status_columns={},
            )


register.inventory_plugin(
    name="win_disks",
    inventory_function=inventory_win_disks,
)
