#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated

checkname = "netscaler_mem"

info = [["4.2", "23"]]

discovery = {"": [(None, {})]}

checks = {
    "": [
        (
            None,
            {"levels": (80.0, 90.0)},
            [
                (
                    0,
                    "Usage: 4.20% - 989 KiB of 23.0 MiB",
                    [
                        (
                            "mem_used",
                            1012924.4160000001,
                            19293798.400000002,
                            21705523.2,
                            0,
                            24117248.0,
                        )
                    ],
                )
            ],
        )
    ]
}
