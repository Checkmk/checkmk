#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated


checkname = "quanta_temperature"


info = [
    [
        ["1", "3", "Temp_PCI1_Outlet\x01", "41", "85", "80", "-99", "-99"],
        ["2", "3", "Temp_CPU0_Inlet", "37", "75", "70", "-99", "-99"],
        ["2", "3", "Temp_CPU1_Inlet", "37", "75", "-99", "-99", "-99"],
        ["7", "1", "Temp_DIMM_AB", "-99", "85", "84", "-99", "-99"],
        ["7", "2", "Temp_DIMM_CD", "-99", "85", "84", "95", "100"],
    ]
]


discovery = {
    "": [
        ("Temp_CPU0_Inlet", {}),
        ("Temp_CPU1_Inlet", {}),
        ("Temp_DIMM_AB", {}),
        ("Temp_DIMM_CD", {}),
        ("Temp_PCI1_Outlet", {}),
    ]
}


checks = {
    "": [
        ("Temp_CPU0_Inlet", {}, [(0, "37.0 \xb0C", [("temp", 37.0, 70.0, 75.0, None, None)])]),
        ("Temp_CPU1_Inlet", {}, [(0, "37.0 \xb0C", [("temp", 37.0, 75.0, 75.0, None, None)])]),
        ("Temp_DIMM_AB", {}, [(1, "Status: other", [])]),
        ("Temp_DIMM_CD", {}, [(3, "Status: unknown", [])]),
        ("Temp_PCI1_Outlet", {}, [(0, "41.0 \xb0C", [("temp", 41.0, 80.0, 85.0, None, None)])]),
    ]
}
