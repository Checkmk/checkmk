#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated


checkname = "ibm_svc_enclosure"


info = [
    [
        "1",
        "online",
        "control",
        "yes",
        "0",
        "io_grp0",
        "2072-24C",
        "7804037",
        "2",
        "1",
        "2",
        "2",
        "24",
    ],
    [
        "2",
        "online",
        "expansion",
        "yes",
        "0",
        "io_grp0",
        "2072-24E",
        "7804306",
        "2",
        "0",
        "2",
        "2",
        "24",
    ],
    [
        "3",
        "online",
        "expansion",
        "yes",
        "0",
        "io_grp0",
        "2072-24E",
        "7804326",
        "2",
        "1",
        "2",
        "2",
        "24",
    ],
    [
        "4",
        "online",
        "expansion",
        "yes",
        "0",
        "io_grp0",
        "2072-24E",
        "7804352",
        "2",
        "2",
        "2",
        "2",
        "24",
    ],
]


discovery = {"": [("1", {}), ("2", {}), ("3", {}), ("4", {})]}


checks = {
    "": [
        (
            "1",
            {"levels_lower_online_canisters": (2, 0)},
            [
                (0, "Status: online", []),
                (1, "Online canisters: 1 (warn/crit below 2/0) of 2", []),
                (0, "Online PSUs: 2 of 2", []),
            ],
        ),
        (
            "2",
            {"levels_lower_online_canisters": (-1, -1)},
            [
                (0, "Status: online", []),
                (0, "Online canisters: 0 of 2", []),
                (0, "Online PSUs: 2 of 2", []),
            ],
        ),
        (
            "3",
            {},
            [
                (0, "Status: online", []),
                (2, "Online canisters: 1 (warn/crit below 2/2) of 2", []),
                (0, "Online PSUs: 2 of 2", []),
            ],
        ),
        (
            "4",
            {},
            [
                (0, "Status: online", []),
                (0, "Online canisters: 2 of 2", []),
                (0, "Online PSUs: 2 of 2", []),
            ],
        ),
    ]
}
