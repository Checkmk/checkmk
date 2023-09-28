#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated


checkname = "aix_lvm"


info = [
    ["rootvg:"],
    ["LV", "NAME", "TYPE", "LPs", "PPs", "PVs", "LV", "STATE", "MOUNT", "POINT"],
    ["hd5", "boot", "1", "4", "2", "closed/syncd", "N/A"],
    ["hd6", "paging", "119", "238", "2", "open/syncd", "N/A"],
    ["hd8", "jfs2log", "1", "3", "2", "open/syncd", "N/A"],
]


discovery = {
    "": [
        ("rootvg/hd5", None),
        ("rootvg/hd6", None),
        ("rootvg/hd8", None),
    ]
}


checks = {
    "": [
        ("rootvg/hd5", {}, [(1, "LV Mirrors are misaligned between physical volumes(!)", [])]),
        ("rootvg/hd6", {}, [(0, "LV is open/syncd", [])]),
        ("rootvg/hd8", {}, [(0, "LV is open/syncd", [])]),
    ]
}
