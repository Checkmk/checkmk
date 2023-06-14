#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated
checkname = "netapp_api_aggr"

info = [
    ["aggregation aggr0_sas_mirror", "size-available 30436616933376", "size-total 80672545427456"],
    ["aggregation aggr1_sata", "size-available 32045210935296", "size-total 128001905786880"],
]

discovery = {"": [("aggr0_sas_mirror", {}), ("aggr1_sata", {})]}

checks = {
    "": [
        (
            "aggr0_sas_mirror",
            {
                "levels": (80.0, 90.0),
                "magic_normsize": 20,
                "levels_low": (50.0, 60.0),
                "trend_range": 24,
                "trend_perfdata": True,
                "show_levels": "onmagic",
                "inodes_levels": (10.0, 5.0),
                "show_inodes": "onlow",
                "show_reserved": False,
            },
            [
                (
                    0,
                    "Used: 62.27% - 45.7 TiB of 73.4 TiB",
                    [
                        (
                            "fs_used",
                            47908714.765625,
                            61548267.690625,
                            69241801.15195313,
                            0,
                            76935334.61328125,
                        ),
                        ("fs_free", 29026619.84765625, None, None, 0, None),
                        ("fs_used_percent", 62.27140624842955, 80.0, 90.0, 0.0, 100.0),
                        ("fs_size", 76935334.61328125, None, None, 0, None),
                    ],
                )
            ],
        ),
        (
            "aggr1_sata",
            {
                "levels": (80.0, 90.0),
                "magic_normsize": 20,
                "levels_low": (50.0, 60.0),
                "trend_range": 24,
                "trend_perfdata": True,
                "show_levels": "onmagic",
                "inodes_levels": (10.0, 5.0),
                "show_inodes": "onlow",
                "show_reserved": False,
            },
            [
                (
                    0,
                    "Used: 74.97% - 87.3 TiB of 116 TiB",
                    [
                        ("fs_used", 91511435.3671875, 97657704.0, 109864917.0, 0, 122072130.0),
                        ("fs_free", 30560694.6328125, None, None, 0, None),
                        ("fs_used_percent", 74.96505170114382, 80.0, 90.0, 0.0, 100.0),
                        ("fs_size", 122072130.0, None, None, 0, None),
                    ],
                )
            ],
        ),
    ]
}
