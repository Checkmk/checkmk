#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.base.plugins.agent_based import windows_intel_bonding

DATA = [
    ["Caption", "Name", "RedundancyStatus"],
    ["Bond_10.4", "{714F579F-D17A-40DC-B684-083C561EE352}", "2"],
    #
    ["###"],
    ["AdapterFunction", "AdapterStatus", "GroupComponent", "PartComponent"],
    [
        "1",
        "1",
        'IANet_TeamOfAdapters.CreationClassName="IANet_TeamOfAdapters",Name="{714F579F-D17A-40DC-B684-083C561EE352}"',
        'IANet_PhysicalEthernetAdapter.CreationClassName="IANet_PhysicalEthernetAdapter",DeviceID="{18EC3002-F03B-4B69-AD88-BFEB700460DC}",SystemCreationClassName="Win32_ComputerSystem",SystemName="Z3061021"',
    ],
    [
        "2",
        "2",
        'IANet_TeamOfAdapters.CreationClassName="IANet_TeamOfAdapters",Name="{714F579F-D17A-40DC-B684-083C561EE352}"',
        'IANet_PhysicalEthernetAdapter.CreationClassName="IANet_PhysicalEthernetAdapter",DeviceID="{1EDEBE50-005F-4533-BAFC-E863617F1030}",SystemCreationClassName="Win32_ComputerSystem",SystemName="Z3061021"',
    ],
    #
    ["###"],
    ["AdapterStatus", "Caption", "DeviceID"],
    [
        "51",
        "TEAM",
        ":",
        "Bond_10.4",
        "-",
        "Intel(R)",
        "Gigabit",
        "ET",
        "Dual",
        "Port",
        "Server",
        "Adapter",
        "{18EC3002-F03B-4B69-AD88-BFEB700460DC}",
    ],
    [
        "51",
        "TEAM",
        ":",
        "Bond_10.4",
        "-",
        "Intel(R)",
        "Gigabit",
        "ET",
        "Dual",
        "Port",
        "Server",
        "Adapter",
        "#2",
        "{1EDEBE50-005F-4533-BAFC-E863617F1030}",
    ],
    [
        "35",
        "Broadcom",
        "BCM5709C",
        "NetXtreme",
        "II",
        "GigE",
        "(NDIS",
        "VBD",
        "Client)",
        "#43",
        "{55799336-A84B-4DA5-8EB9-B7426AA1AB75}",
    ],
    [
        "35",
        "Broadcom",
        "BCM5709C",
        "NetXtreme",
        "II",
        "GigE",
        "(NDIS",
        "VBD",
        "Client)",
        "#35",
        "{7DB9B461-FAC0-4763-9AF9-9A6CA6648188}",
    ],
    [
        "35",
        "Broadcom",
        "BCM5709C",
        "NetXtreme",
        "II",
        "GigE",
        "(NDIS",
        "VBD",
        "Client)",
        "#40",
        "{82AE1F27-BF28-4E30-AC3D-809DF5FF0D39}",
    ],
    [
        "35",
        "Broadcom",
        "BCM5709C",
        "NetXtreme",
        "II",
        "GigE",
        "(NDIS",
        "VBD",
        "Client)",
        "#38",
        "{DC918766-F61C-4801-92F8-E5532907EA0D}",
    ],
]


def test_parse_failover() -> None:
    assert windows_intel_bonding.parse_windows_intel_bonding(DATA) == {
        "Bond_10.4": {
            "active": "Intel(R) Gigabit ET Dual Port Server Adapter",
            "interfaces": {
                "Intel(R) Gigabit ET Dual Port Server Adapter": {"status": "up"},
                "Intel(R) Gigabit ET Dual Port Server Adapter #2": {"status": "up"},
            },
            "mode": "2",
            "primary": "Intel(R) Gigabit ET Dual Port Server Adapter",
            "status": "up",
        }
    }
