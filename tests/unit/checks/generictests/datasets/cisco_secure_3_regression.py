#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated

# Regression test for SUP-27718 / werk 18739:
# Verify that ports with actual violation evidence still trigger CRITICAL
# even when status == 3, i.e. the false-positive skip condition does not
# suppress real violations.

checkname = "cisco_secure"

info = [
    [
        ["1", "GigabitEthernet0/1", "1"],
        ["2", "GigabitEthernet0/2", "1"],
        ["3", "GigabitEthernet0/3", "1"],
    ],
    [
        # status=3, violation_count=3, no mac -> CRIT (violation_count > 0 bypasses skip)
        ["1", "1", "3", "3", ""],
        # status=3, violation_count=0, mac set -> CRIT (lastmac set bypasses skip)
        # "ABC" encodes to 41:42:43 via _sanitize_mac
        ["2", "1", "3", "0", "ABC"],
        # status=3, violation_count=0, no mac -> skipped (the false-positive case)
        ["3", "1", "3", "0", ""],
    ],
]

discovery = {"": [(None, None)]}

checks = {
    "": [
        (
            None,
            {},
            [
                (
                    2,
                    "Port GigabitEthernet0/1: shutdown due to security violation (violation count: 3, last MAC: )",
                    [],
                ),
                (
                    2,
                    "Port GigabitEthernet0/2: shutdown due to security violation (violation count: 0, last MAC: 41:42:43)",
                    [],
                ),
            ],
        )
    ]
}
