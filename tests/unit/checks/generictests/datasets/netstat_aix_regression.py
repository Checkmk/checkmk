#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated


checkname = "netstat"


info = [
    ["tcp4", "0", "0", "127.0.0.1.32832", "127.0.0.1.32833", "ESTABLISHED"],
    ["tcp", "0", "0", "172.22.182.179.45307", "172.22.182.179.3624", "ESTABLISHED"],
]


discovery = {"": []}

checks = {"": [("connections", {"min_states": ("no_levels", None), "max_states": ("no_levels", None)}, [(0, "Matching entries found: 2", [("connections", 2)])])]}
