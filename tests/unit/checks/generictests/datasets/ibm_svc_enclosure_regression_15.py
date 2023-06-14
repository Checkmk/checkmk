#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated


checkname = "ibm_svc_enclosure"


info = [
    [
        "5",
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
        "0",
        "0",
    ]
]


discovery = {"": [("5", {})]}


checks = {
    "": [
        (
            "5",
            {},
            [
                (0, "Status: online", []),
                (0, "Online canisters: 2 of 2", []),
                (0, "Online PSUs: 2 of 2", []),
                (0, "Online fan modules: 0 of 0", []),
            ],
        )
    ]
}
