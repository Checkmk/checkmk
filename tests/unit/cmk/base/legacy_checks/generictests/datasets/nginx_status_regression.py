#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated


checkname = "nginx_status"


freeze_time = "2019-10-02 08:15:35"


info = [
    ["127.0.0.1", "80", "Active", "connections:", "10"],
    ["127.0.0.1", "80", "serveracceptshandledrequests"],
    ["127.0.0.1", "80", "12", "10", "120"],
    ["127.0.0.1", "80", "Reading:", "2", "Writing:", "1", "Waiting:", "3"],
    ["127.0.1.1", "80", "Active", "connections:", "24"],
    ["127.0.1.1", "80", "server", "accepts", "handled", "requests"],
    ["127.0.1.1", "80", "23", "42", "323"],
    ["127.0.1.1", "80", "Reading:", "1", "Writing:", "5", "Waiting:", "0"],
]


discovery = {"": [("127.0.0.1:80", {}), ("127.0.1.1:80", {})]}


checks = {
    "": [
        (
            "127.0.0.1:80",
            {},
            [
                (
                    0,
                    "Active: 10 (2 reading, 1 writing, 3 waiting)",
                    [
                        ("active", 10, None, None, None, None),
                    ],
                ),
                (
                    0,
                    "",
                    [
                        ("reading", 2, None, None, None, None),
                        ("writing", 1, None, None, None, None),
                        ("waiting", 3, None, None, None, None),
                    ],
                ),
                (
                    0,
                    "Requests: 0.02/s (12.00/Connection)",
                    [("requests", 0.01674808094905792, None, None, None, None)],
                ),
                (0, "Accepted: 0.00/s", [("accepted", 12, None, None, None, None)]),
                (0, "Handled: 0.00/s", [("handled", 10, None, None, None, None)]),
            ],
        ),
        (
            "127.0.1.1:80",
            {},
            [
                (
                    0,
                    "Active: 24 (1 reading, 5 writing, 0 waiting)",
                    [
                        ("active", 24, None, None, None, None),
                    ],
                ),
                (
                    0,
                    "",
                    [
                        ("reading", 1, None, None, None, None),
                        ("writing", 5, None, None, None, None),
                        ("waiting", 0, None, None, None, None),
                    ],
                ),
                (
                    0,
                    "Requests: 0.05/s (7.69/Connection)",
                    [("requests", 0.045080251221214236, None, None, None, None)],
                ),
                (0, "Accepted: 0.00/s", [("accepted", 23, None, None, None, None)]),
                (0, "Handled: 0.01/s", [("handled", 42, None, None, None, None)]),
            ],
        ),
    ]
}


mock_item_state = {"": (1569996970, 0)}
