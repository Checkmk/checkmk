#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated


checkname = "veeam_jobs"


info = [
    ["VMware_Server", "Backup", "Stopped", "Success", "21.01.2019 00:10:22", "21.01.2019 00:29:12"],
    [
        "Lehrer_Rechner",
        "Backup",
        "Stopped",
        "Success",
        "23.07.2018 13:08:37",
        "23.07.2018 13:27:44",
    ],
    [
        "Windows_Admin_PC",
        "Backup",
        "Stopped",
        "Success",
        "20.01.2019 22:00:06",
        "20.01.2019 22:02:42",
    ],
    ["Lehrer Rechner"],
]


discovery = {
    "": [
        ("Lehrer Rechner", None),
        ("Lehrer_Rechner", None),
        ("VMware_Server", None),
        ("Windows_Admin_PC", None),
    ]
}


checks = {
    "": [
        ("Lehrer Rechner", {}, []),
        (
            "Lehrer_Rechner",
            {},
            [
                (
                    0,
                    "State: Stopped, Result: Success, Creation time: 23.07.2018 13:08:37, End time: 23.07.2018 13:27:44, Type: Backup",
                    [],
                )
            ],
        ),
        (
            "VMware_Server",
            {},
            [
                (
                    0,
                    "State: Stopped, Result: Success, Creation time: 21.01.2019 00:10:22, End time: 21.01.2019 00:29:12, Type: Backup",
                    [],
                )
            ],
        ),
        (
            "Windows_Admin_PC",
            {},
            [
                (
                    0,
                    "State: Stopped, Result: Success, Creation time: 20.01.2019 22:00:06, End time: 20.01.2019 22:02:42, Type: Backup",
                    [],
                )
            ],
        ),
    ]
}
