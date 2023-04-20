#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# type: ignore


checkname = "tsm_scratch"


info = [
    ["Foo23", "SELECT:", "No", "match", "found", "using", "this", "criteria."],
    ["Bar42", "R\xfcckkehrcode", "11."],
    ["Baz123", "6", "Any.Lib1"],
    ["default", "8", "Any.Lib2"],
]


discovery = {
    "": [
        ("Any.Lib2", "tsm_scratch_default_levels"),
        ("Baz123 / Any.Lib1", "tsm_scratch_default_levels"),
    ]
}


checks = {
    "": [
        ("Any.Lib2", (5, 7), [(0, "Found tapes: 8", [("tapes_free", 8, None, None, None, None)])]),
        (
            "Baz123 / Any.Lib1",
            (5, 7),
            [
                (
                    1,
                    "Found tapes: 6 (warn/crit below 7/5)",
                    [("tapes_free", 6, None, None, None, None)],
                )
            ],
        ),
    ]
}
