#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated


checkname = "md"


info = [
    ["Personalities", ":", "[linear]", "[raid0]", "[raid1]"],
    ["md1", ":", "active", "linear", "sda3[0]", "sdb3[1]"],
    ["491026496", "blocks", "64k", "rounding"],
    ["md0", ":", "active", "raid0", "sda2[0]", "sdb2[1]"],
    ["2925532672", "blocks", "64k", "chunks"],
    ["unused", "devices:", "<none>"],
]


discovery = {"": [("md1", None)]}


checks = {"": [("md1", {}, [(0, "Status: active", []), (0, "Spare: 0, Failed: 0, Active: 2", [])])]}
