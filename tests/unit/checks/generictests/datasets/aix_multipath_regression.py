#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# type: ignore


checkname = "aix_multipath"


info = [
    ["hdisk0", "vscsi0", "Enabled"],
    ["hdisk1", "fscsi0", "Enabled"],
    ["hdisk1", "fscsi1", "Enabled"],
    ["hdisk2", "fscsi0", "Enabled"],
    ["hdisk2", "fscsi1", "Missing"],
    ["hdisk2", "fscsi3", "Enabled"],
    ["hdisk2", "fscsi4", "Enabled"],
    ["hdisk3", "fscsi1", "Missing"],
    ["hdisk3", "fscsi2", "Missing"],
    ["hdisk3", "fscsi3", "Missing"],
    ["hdisk3", "fscsi4", "Enabled"],
    ["hdisk3", "fscsi5", "Enabled"],
    ["hdisk3", "fscsi6", "Enabled"],
]


discovery = {
    "": [
        ("hdisk0", {"paths": 1}),
        ("hdisk1", {"paths": 2}),
        ("hdisk2", {"paths": 4}),
        ("hdisk3", {"paths": 6}),
    ]
}


checks = {
    "": [
        ("hdisk0", {"paths": 1}, [(0, "1 paths total", [])]),
        ("hdisk1", {"paths": 2}, [(0, "2 paths total", [])]),
        ("hdisk2", {"paths": 4}, [(1, "1 paths not enabled (!), 4 paths total", [])]),
        ("hdisk3", {"paths": 6}, [(2, "3 paths not enabled (!!), 6 paths total", [])]),
    ]
}
