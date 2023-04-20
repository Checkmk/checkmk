#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# type: ignore


checkname = "juniper_trpz_flash"


info = [["51439616", "62900224"]]


discovery = {"": [(None, "juniper_trpz_flash_default_levels")]}


checks = {
    "": [
        (
            None,
            (90.0, 95.0),
            [
                (
                    0,
                    "Used: 49.1 MiB of 60.0 MiB ",
                    [("used", 51439616.0, 56610201.6, 59755212.8, 0, 62900224.0)],
                )
            ],
        )
    ]
}
