#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code=var-annotated


checkname = "3ware_disks"


mock_item_state = {
    "": {
        "packets_rate": (0, 150512),
    }
}


info = [
    ["p0", "OK", "u0", "465.76", "GB", "SATA", "0", "-", "ST3500418AS"],
    ["p1", "VERIFYING", "u0", "465.76", "GB", "SATA", "1", "-", "ST3500418AS"],
    ["p2", "SMART_FAILURE", "u0", "465.76", "GB", "SATA", "2", "-", "ST3500320SV"],
    ["p3", "FOOBAR", "u0", "465.76", "GB", "SATA", "3", "-", "ST3500418AS"],
]


discovery = {"": [("p0", {}), ("p1", {}), ("p2", {}), ("p3", {})]}


checks = {
    "": [
        (
            "p0",
            {},
            [
                (
                    0,
                    "disk status is OK (unit: u0, size: 465.76,GB, type: SATA, model: ST3500418AS)",
                    [],
                )
            ],
        ),
        (
            "p1",
            {},
            [
                (
                    0,
                    "disk status is VERIFYING (unit: u0, size: 465.76,GB, type: SATA, model: ST3500418AS)",
                    [],
                )
            ],
        ),
        (
            "p2",
            {},
            [
                (
                    1,
                    "disk status is SMART_FAILURE (unit: u0, size: 465.76,GB, type: SATA, model: ST3500320SV)",
                    [],
                )
            ],
        ),
        (
            "p3",
            {},
            [
                (
                    2,
                    "disk status is FOOBAR (unit: u0, size: 465.76,GB, type: SATA, model: ST3500418AS)",
                    [],
                )
            ],
        ),
    ]
}
