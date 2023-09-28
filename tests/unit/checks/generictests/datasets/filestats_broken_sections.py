#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated


checkname = "filestats"

info = [
    ["some garbage in the first line (should be ignored)"],
    ["[[[count_only ok subsection]]]"],
    ["{'type': 'summary', 'count': 23}"],
    ["[[[count_only missing count]]]"],
    ["{'type': 'summary', 'foobar': 42}"],
    ["[[[count_only complete mess]]]"],
    ["{'fooba2adrs: gh"],
    ["[[[count_only empty subsection]]]"],
    ["{}"],
]

discovery = {
    "": [
        ("ok subsection", {}),
        ("missing count", {}),
        ("complete mess", {}),
        ("empty subsection", {}),
    ]
}

checks = {
    "": [
        ("broken subsection", {}, []),
        ("complete mess", {}, []),
        ("empty subsection", {}, []),
        (
            "ok subsection",
            {},
            [
                (0, "Files in total: 23", [("file_count", 23, None, None, None, None)]),
            ],
        ),
    ]
}
