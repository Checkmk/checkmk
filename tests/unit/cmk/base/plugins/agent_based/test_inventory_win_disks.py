#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.base.plugins.agent_based.agent_based_api.v1 import TableRow
from cmk.base.plugins.agent_based.inventory_win_disks import inventory_win_disks, parse_win_disks

from .utils_inventory import sort_inventory_result


@pytest.mark.parametrize(
    "string_table, expected_result",
    [
        ([], []),
        (
            [
                ["DeviceID                    ", " \\.\\PHYSICALDRIVE0"],
                ["Partitions                  ", " 2"],
                ["InterfaceType               ", " IDE"],
                ["Size                        ", " 32210196480"],
                ["Caption                     ", " VBOX HARDDISK ATA Device"],
                ["Description                 ", " Laufwerk"],
                ["Manufacturer                ", " (Standardlaufwerke)"],
                ["MediaType                   ", " Fixed hard disk media"],
                ["Model                       ", " VBOX HARDDISK ATA Device"],
                ["Name                        ", " \\.\\PHYSICALDRIVE0"],
                ["SerialNumber                ", " 42566539323537333930652d3836636263352065"],
                ["CapabilityDescriptions      ", " {Random Access, Supports Writing}"],
                ["BytesPerSector              ", " 512"],
                ["Index                       ", " 0"],
                ["FirmwareRevision            ", " 1.0"],
                ["MediaLoaded                 ", " True"],
                ["Status                      ", " OK"],
                ["SectorsPerTrack             ", " 63"],
                ["TotalCylinders              ", " 3916"],
                ["TotalHeads                  ", " 255"],
                ["TotalSectors                ", " 62910540"],
                ["TotalTracks                 ", " 998580"],
                ["TracksPerCylinder           ", " 255"],
                ["Capabilities                ", " {3, 4}"],
                ["Signature                   ", " 645875120"],
                ["SCSIBus                     ", " 0"],
                ["SCSILogicalUnit             ", " 0"],
                ["SCSIPort                    ", " 2"],
                ["SCSITargetId                ", " 0"],
            ],
            [
                TableRow(
                    path=["hardware", "storage", "disks"],
                    key_columns={
                        "fsnode": "\\.\\PHYSICALDRIVE0",
                    },
                    inventory_columns={
                        "vendor": "(Standardlaufwerke)",
                        "bus": "IDE",
                        "product": "VBOX HARDDISK ATA Device",
                        "serial": "42566539323537333930652d3836636263352065",
                        "size": 32210196480,
                        "type": "Fixed hard disk media",
                        "signature": 645875120,
                        "local": True,
                    },
                    status_columns={},
                ),
            ],
        ),
        (
            [
                ["DeviceID                    ", " \\.\\PHYSICALDRIVE0"],
                ["Partitions                  ", " 2"],
                ["InterfaceType               ", " IDE"],
                ["Size                        ", " 32210196480"],
                ["Caption                     ", " VBOX HARDDISK ATA Device"],
                ["Description                 ", " Laufwerk"],
                ["Manufacturer                ", " (Standardlaufwerke)"],
                ["MediaType                   ", " Fixed hard disk media"],
                ["Model                       ", " VBOX HARDDISK ATA Device"],
                ["Name                        ", " \\.\\PHYSICALDRIVE0"],
                ["SerialNumber                ", " 42566539323537333930652d3836636263352065"],
                ["CapabilityDescriptions      ", " {Random Access, Supports Writing}"],
                ["BytesPerSector              ", " 512"],
                ["Index                       ", " 0"],
                ["FirmwareRevision            ", " 1.0"],
                ["MediaLoaded                 ", " True"],
                ["Status                      ", " OK"],
                ["SectorsPerTrack             ", " 63"],
                ["TotalCylinders              ", " 3916"],
                ["TotalHeads                  ", " 255"],
                ["TotalSectors                ", " 62910540"],
                ["TotalTracks                 ", " 998580"],
                ["TracksPerCylinder           ", " 255"],
                ["Capabilities                ", " {3, 4}"],
                ["Signature                   ", " 645875120"],
                ["SCSIBus                     ", " 0"],
                ["SCSILogicalUnit             ", " 0"],
                ["SCSIPort                    ", " 2"],
                ["SCSITargetId                ", " 0"],
                ["DeviceID                    ", " \\.\\PHYSICALDRIVE1"],
                ["Partitions                  ", " 2"],
                ["InterfaceType               ", " IDE"],
                ["Size                        ", " 32210196480"],
                ["Caption                     ", " VBOX HARDDISK ATA Device"],
                ["Description                 ", " Laufwerk"],
                ["Manufacturer                ", " (Standardlaufwerke)"],
                ["MediaType                   ", " Fixed hard disk media"],
                ["Model                       ", " VBOX HARDDISK ATA Device"],
                ["Name                        ", " \\.\\PHYSICALDRIVE1"],
                ["SerialNumber                ", " 42566539323537333930652d3836636263352065"],
                ["CapabilityDescriptions      ", " {Random Access, Supports Writing}"],
                ["BytesPerSector              ", " 512"],
                ["Index                       ", " 0"],
                ["FirmwareRevision            ", " 1.0"],
                ["MediaLoaded                 ", " True"],
                ["Status                      ", " OK"],
                ["SectorsPerTrack             ", " 63"],
                ["TotalCylinders              ", " 3916"],
                ["TotalHeads                  ", " 255"],
                ["TotalSectors                ", " 62910540"],
                ["TotalTracks                 ", " 998580"],
                ["TracksPerCylinder           ", " 255"],
                ["Capabilities                ", " {3, 4}"],
                ["Signature                   ", " 645875120"],
                ["SCSIBus                     ", " 0"],
                ["SCSILogicalUnit             ", " 0"],
                ["SCSIPort                    ", " 2"],
                ["SCSITargetId                ", " 0"],
            ],
            [
                TableRow(
                    path=["hardware", "storage", "disks"],
                    key_columns={
                        "fsnode": "\\.\\PHYSICALDRIVE0",
                    },
                    inventory_columns={
                        "vendor": "(Standardlaufwerke)",
                        "bus": "IDE",
                        "product": "VBOX HARDDISK ATA Device",
                        "serial": "42566539323537333930652d3836636263352065",
                        "size": 32210196480,
                        "type": "Fixed hard disk media",
                        "signature": 645875120,
                        "local": True,
                    },
                    status_columns={},
                ),
                TableRow(
                    path=["hardware", "storage", "disks"],
                    key_columns={
                        "fsnode": "\\.\\PHYSICALDRIVE1",
                    },
                    inventory_columns={
                        "vendor": "(Standardlaufwerke)",
                        "bus": "IDE",
                        "product": "VBOX HARDDISK ATA Device",
                        "serial": "42566539323537333930652d3836636263352065",
                        "size": 32210196480,
                        "type": "Fixed hard disk media",
                        "signature": 645875120,
                        "local": True,
                    },
                    status_columns={},
                ),
            ],
        ),
    ],
)
def test_inventory_win_disks(string_table, expected_result):
    assert sort_inventory_result(
        inventory_win_disks(parse_win_disks(string_table))
    ) == sort_inventory_result(expected_result)
