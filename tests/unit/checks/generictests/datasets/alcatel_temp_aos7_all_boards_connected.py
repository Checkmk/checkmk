#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated

checkname = "alcatel_temp_aos7"

info = [
    ["44", "44", "44", "44", "44", "44", "44", "44", "44", "44", "44", "44", "44", "44", "44", "44"]
]

discovery = {
    "": [
        ("CFMA", {}),
        ("CFMB", {}),
        ("CFMC", {}),
        ("CFMD", {}),
        ("CPMA", {}),
        ("CPMB", {}),
        ("FTA", {}),
        ("FTB", {}),
        ("NI1", {}),
        ("NI2", {}),
        ("NI3", {}),
        ("NI4", {}),
        ("NI5", {}),
        ("NI6", {}),
        ("NI7", {}),
        ("NI8", {}),
    ]
}

checks = {
    "": [
        ("CFMA", {"levels": (45, 50)}, [(0, "44 \xb0C", [("temp", 44, 45, 50, None, None)])]),
        ("CFMB", {"levels": (45, 50)}, [(0, "44 \xb0C", [("temp", 44, 45, 50, None, None)])]),
        ("CFMC", {"levels": (45, 50)}, [(0, "44 \xb0C", [("temp", 44, 45, 50, None, None)])]),
        ("CFMD", {"levels": (45, 50)}, [(0, "44 \xb0C", [("temp", 44, 45, 50, None, None)])]),
        ("CPMA", {"levels": (45, 50)}, [(0, "44 \xb0C", [("temp", 44, 45, 50, None, None)])]),
        ("CPMB", {"levels": (45, 50)}, [(0, "44 \xb0C", [("temp", 44, 45, 50, None, None)])]),
        ("FTA", {"levels": (45, 50)}, [(0, "44 \xb0C", [("temp", 44, 45, 50, None, None)])]),
        ("FTB", {"levels": (45, 50)}, [(0, "44 \xb0C", [("temp", 44, 45, 50, None, None)])]),
        ("NI1", {"levels": (45, 50)}, [(0, "44 \xb0C", [("temp", 44, 45, 50, None, None)])]),
        ("NI2", {"levels": (45, 50)}, [(0, "44 \xb0C", [("temp", 44, 45, 50, None, None)])]),
        ("NI3", {"levels": (45, 50)}, [(0, "44 \xb0C", [("temp", 44, 45, 50, None, None)])]),
        ("NI4", {"levels": (45, 50)}, [(0, "44 \xb0C", [("temp", 44, 45, 50, None, None)])]),
        ("NI5", {"levels": (45, 50)}, [(0, "44 \xb0C", [("temp", 44, 45, 50, None, None)])]),
        ("NI6", {"levels": (45, 50)}, [(0, "44 \xb0C", [("temp", 44, 45, 50, None, None)])]),
        ("NI7", {"levels": (45, 50)}, [(0, "44 \xb0C", [("temp", 44, 45, 50, None, None)])]),
        ("NI8", {"levels": (45, 50)}, [(0, "44 \xb0C", [("temp", 44, 45, 50, None, None)])]),
    ]
}
