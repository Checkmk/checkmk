#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated

checkname = "poseidon_inputs"

info = [
    ["1", "Bezeichnung Eingang 1", "1", "0"],
    ["0", "Bezeichnung Eingang 2", "2", "0"],
    ["0", "Bezeichnung Eingang 3", "1", "1"],
    ["0", "Bezeichnung Eingang 4", "1", "1"],
    ["0", "Comm Monitor 1", "0", "0"],
]

discovery = {
    "": [
        ("Bezeichnung Eingang 1", {}),
        ("Bezeichnung Eingang 2", {}),
        ("Bezeichnung Eingang 3", {}),
        ("Bezeichnung Eingang 4", {}),
        ("Comm Monitor 1", {}),
    ]
}

checks = {
    "": [
        (
            "Bezeichnung Eingang 1",
            {},
            [
                (0, "Bezeichnung Eingang 1: AlarmSetup: activeOff", []),
                (0, "Alarm State: normal", []),
                (0, "Values on", []),
            ],
        ),
        (
            "Bezeichnung Eingang 2",
            {},
            [
                (0, "Bezeichnung Eingang 2: AlarmSetup: activeOn", []),
                (0, "Alarm State: normal", []),
                (0, "Values off", []),
            ],
        ),
        (
            "Bezeichnung Eingang 3",
            {},
            [
                (0, "Bezeichnung Eingang 3: AlarmSetup: activeOff", []),
                (2, "Alarm State: alarm", []),
                (0, "Values off", []),
            ],
        ),
        (
            "Bezeichnung Eingang 4",
            {},
            [
                (0, "Bezeichnung Eingang 4: AlarmSetup: activeOff", []),
                (2, "Alarm State: alarm", []),
                (0, "Values off", []),
            ],
        ),
        (
            "Comm Monitor 1",
            {},
            [
                (0, "Comm Monitor 1: AlarmSetup: inactive", []),
                (0, "Alarm State: normal", []),
                (0, "Values off", []),
            ],
        ),
    ]
}
