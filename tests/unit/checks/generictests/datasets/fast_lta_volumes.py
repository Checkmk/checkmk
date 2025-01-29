#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated
from cmk.plugins.lib.df import FILESYSTEM_DEFAULT_LEVELS

checkname = "fast_lta_volumes"

info = [["Archiv_Test", "1000000000000", "10000000000"], ["Archiv_Test_1", "", ""]]

discovery = {"": [("Archiv_Test", {})]}

checks = {
    "": [
        (
            "Archiv_Test",
            FILESYSTEM_DEFAULT_LEVELS,
            [
                (
                    0,
                    "Used: 1.00% - 9.31 GiB of 931 GiB",
                    [
                        (
                            "fs_used",
                            9536.7431640625,
                            762939.453125,
                            858306.884765625,
                            0,
                            953674.31640625,
                        ),
                        ("fs_free", 944137.5732421875, None, None, 0, None),
                        ("fs_used_percent", 1.0, 80.0, 90.0, 0.0, 100.0),
                        ("fs_size", 953674.31640625, None, None, 0, None),
                    ],
                )
            ],
        )
    ]
}
