#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code=var-annotated


checkname = "citrix_sessions"


info = [["sessions", "1"], ["active_sessions", "1"], ["inactive_sessions", "0"]]


discovery = {
    "": [
        (
            None,
            {
                "total": (60, 65),
                "active": (60, 65),
                "inactive": (10, 15),
            },
        ),
    ],
}


checks = {
    "": [
        (
            None,
            {"active": (60, 65), "inactive": (10, 15), "total": (60, 65)},
            [
                (0, "Total: 1", [("total", 1, 60, 65, None, None)]),
                (0, "Active: 1", [("active", 1, 60, 65, None, None)]),
                (0, "Inactive: 0", [("inactive", 0, 10, 15, None, None)]),
            ],
        )
    ]
}
