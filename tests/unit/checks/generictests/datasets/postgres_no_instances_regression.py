#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated

checkname = "postgres_instances"

info = [
    ["[[[postgres]]]"],
    [
        "psql (PostgreSQL) 10.12 (Ubuntu 10.12-0ubuntu0.18.04.1)",
    ],
]

discovery = {"": [("POSTGRES", {})]}

checks = {
    "": [
        (
            "POSTGRES",
            {},
            [
                (
                    2,
                    "Instance POSTGRES not running or postgres DATADIR name is not identical with instance name.",
                    [],
                )
            ],
        )
    ]
}
