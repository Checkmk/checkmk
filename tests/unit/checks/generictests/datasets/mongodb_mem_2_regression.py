#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated


checkname = "mongodb_mem"


info = [
    ["resident", "79"],
    ["supported", "True"],
    ["virtual", "1021"],
    ["mappedWithJournal", "0"],
    ["mapped", "0"],
    ["bits", "64"],
    ["note", "fields", "vary", "by", "platform"],
    ["page_faults", "9"],
]


discovery = {"": [(None, {})]}


checks = {
    "": [
        (
            None,
            {},
            [
                (
                    0,
                    "Resident usage: 79.0 MiB",
                    [("process_resident_size", 82837504, None, None, None, None)],
                ),
                (
                    0,
                    "Virtual usage: 1021 MiB",
                    [("process_virtual_size", 1070596096, None, None, None, None)],
                ),
                (0, "Mapped usage: 0 B", [("process_mapped_size", 0, None, None, None, None)]),
            ],
        )
    ]
}
