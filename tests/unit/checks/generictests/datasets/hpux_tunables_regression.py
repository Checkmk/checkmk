#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated


checkname = "hpux_tunables"


info = [
    ["Tunable:", "maxfiles_lim"],
    ["Usage:", "152"],
    ["Setting:", "63488"],
    ["Percentage:", "0.2"],
    ["Tunable:", "nkthread"],
    ["Usage:", "1314"],
    ["Setting:", "8416"],
    ["Percentage:", "15.6"],
    ["Tunable:", "nproc"],
    ["Usage:", "462"],
    ["Setting:", "4200"],
    ["Percentage:", "11.0"],
    ["Tunable:", "semmni"],
    ["Usage:", "41"],
    ["Setting:", "4200"],
    ["Percentage:", "1.0"],
    ["Tunable:", "semmns"],
    ["Usage:", "1383"],
    ["Setting:", "8400"],
    ["Percentage:", "16.5"],
    ["Tunable:", "shmseg"],
    ["Usage:", "3"],
    ["Setting:", "512"],
    ["Percentage:", "0.6"],
]


discovery = {
    "maxfiles_lim": [(None, {})],
    "nkthread": [(None, {})],
    "nproc": [(None, {})],
    "semmni": [(None, {})],
    "semmns": [(None, {})],
    "shmseg": [(None, {})],
}


checks = {
    "maxfiles_lim": [
        (
            None,
            {"levels": (85.0, 90.0)},
            [(0, "0.24% used (152/63488 files)", [("files", 152, 53964.8, 57139.2, 0, 63488)])],
        )
    ],
    "nkthread": [
        (
            None,
            {"levels": (80.0, 85.0)},
            [(0, "15.61% used (1314/8416 threads)", [("threads", 1314, 6732.8, 7153.6, 0, 8416)])],
        )
    ],
    "nproc": [
        (
            None,
            {"levels": (90.0, 96.0)},
            [
                (
                    0,
                    "11.00% used (462/4200 processes)",
                    [("processes", 462, 3780.0, 4032.0, 0, 4200)],
                )
            ],
        )
    ],
    "semmni": [
        (
            None,
            {"levels": (85.0, 90.0)},
            [
                (
                    0,
                    "0.98% used (41/4200 semaphore_ids)",
                    [("semaphore_ids", 41, 3570.0, 3780.0, 0, 4200)],
                )
            ],
        )
    ],
    "semmns": [
        (
            None,
            {"levels": (85.0, 90.0)},
            [(0, "16.46% used (1383/8400 entries)", [("entries", 1383, 7140.0, 7560.0, 0, 8400)])],
        )
    ],
    "shmseg": [
        (
            None,
            {"levels": (85.0, 90.0)},
            [(0, "0.59% used (3/512 segments)", [("segments", 3, 435.2, 460.8, 0, 512)])],
        )
    ],
}
