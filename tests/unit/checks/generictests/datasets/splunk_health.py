#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated


checkname = "splunk_health"


info = [
    ["Overall_state", "green"],
    ["File_monitor_input", "green"],
    ["File_monitor_input", "Tailreader-0", "green"],
    ["File_monitor_input", "Batchreader-0", "green"],
    ["Index_processor", "green"],
    ["Index_processor", "Index_optimization", "green"],
    ["Index_processor", "Buckets", "green"],
    ["Index_processor", "Disk_space", "green"],
]


discovery = {"": [(None, {})]}


checks = {
    "": [
        (
            None,
            {"green": 0, "red": 2, "yellow": 1},
            [
                (0, "Overall state: green", []),
                (0, "File monitor input: green", []),
                (0, "Index processor: green", []),
                (
                    0,
                    "\nBatchreader-0 - State: green\nTailreader-0 - State: green\nBuckets - State: green\nDisk space - State: green\nIndex optimization - State: green\n",
                    [],
                ),
            ],
        )
    ]
}
