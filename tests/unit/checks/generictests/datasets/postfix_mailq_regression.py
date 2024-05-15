#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated

checkname = "postfix_mailq"

info = [
    ["[[[]]]"],
    ["QUEUE_deferred", "2", "1"],
    ["QUEUE_active", "4", "3"],
    ["[[[/etc/postfix-internal]]]"],
    ["QUEUE_deferred", "2", "1"],
    ["QUEUE_active", "4", "3"],
]

discovery = {"": [("default", {}), ("/etc/postfix-internal", {})]}

checks = {
    "": [
        (
            "default",
            {"active": (200, 300), "deferred": (10, 20)},
            [
                (
                    0,
                    "Deferred queue length: 1",
                    [("length", 1, 10, 20, None, None), ("size", 2, None, None, None, None)],
                ),
                (
                    0,
                    "Active queue length: 3",
                    [
                        ("mail_queue_active_length", 3, 200, 300, None, None),
                        ("mail_queue_active_size", 4, None, None, None, None),
                    ],
                ),
            ],
        ),
        (
            "/etc/postfix-internal",
            {"active": (200, 300), "deferred": (10, 20)},
            [
                (
                    0,
                    "Deferred queue length: 1",
                    [("length", 1, 10, 20, None, None), ("size", 2, None, None, None, None)],
                ),
                (
                    0,
                    "Active queue length: 3",
                    [
                        ("mail_queue_active_length", 3, 200, 300, None, None),
                        ("mail_queue_active_size", 4, None, None, None, None),
                    ],
                ),
            ],
        ),
    ]
}
