#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated


checkname = "ibm_svc_enclosurestats"


info = [
    ["1", "power_w", "207", "218", "140410113051"],
    ["1", "temp_c", "22", "22", "140410113246"],
    ["1", "temp_f", "71", "71", "140410113246"],
    ["2", "power_w", "126", "128", "140410113056"],
    ["2", "temp_c", "21", "21", "140410113246"],
    ["2", "temp_f", "69", "69", "140410113246"],
    ["3", "power_w", "123", "126", "140410113041"],
    ["3", "temp_c", "22", "22", "140410113246"],
    ["3", "temp_f", "71", "71", "140410113246"],
    ["4", "power_w", "133", "138", "140410112821"],
    ["4", "temp_c", "22", "23", "140410112836"],
    ["4", "temp_f", "71", "73", "140410112836"],
]


discovery = {
    "power": [("1", {}), ("2", {}), ("3", {}), ("4", {})],
    "temp": [("1", {}), ("2", {}), ("3", {}), ("4", {})],
}


checks = {
    "power": [
        ("1", {}, [(0, "207 Watt", [("power", 207, None, None, None, None)])]),
        ("2", {}, [(0, "126 Watt", [("power", 126, None, None, None, None)])]),
        ("3", {}, [(0, "123 Watt", [("power", 123, None, None, None, None)])]),
        ("4", {}, [(0, "133 Watt", [("power", 133, None, None, None, None)])]),
    ],
    "temp": [
        ("1", {"levels": (35, 40)}, [(0, "22 \xb0C", [("temp", 22, 35, 40, None, None)])]),
        ("2", {"levels": (35, 40)}, [(0, "21 \xb0C", [("temp", 21, 35, 40, None, None)])]),
        ("3", {"levels": (35, 40)}, [(0, "22 \xb0C", [("temp", 22, 35, 40, None, None)])]),
        ("4", {"levels": (35, 40)}, [(0, "22 \xb0C", [("temp", 22, 35, 40, None, None)])]),
    ],
}
