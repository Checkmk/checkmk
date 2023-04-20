#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# type: ignore


checkname = "postgres_instances"


info = [
    ["[[[postgres]]]"],
    [
        "30611",
        "/usr/lib/postgresql/10/bin/postgres",
        "-D",
        "/var/lib/postgresql/10/main",
        "-c",
        "config_file=/etc/postgresql/10/main/postgresql.conf",
    ],
]


discovery = {"": [("POSTGRES", {})]}


checks = {"": [("POSTGRES", {}, [(0, "Status: running with PID 30611", [])])]}
