#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated


checkname = "ibm_svc_eventlog"


info = [
    [
        "164",
        "220522214408",
        "enclosure",
        "1",
        "",
        "",
        "alert",
        "no",
        "085044",
        "1114",
        "Enclosure Battery fault type 1",
        "",
        "",
    ]
]


discovery = {
    "": [
        (None, None),
    ]
}


checks = {
    "": [
        (
            None,
            {},
            [
                (
                    1,
                    "1 messages not expired and not yet fixed found in event log, last was: Enclosure Battery fault type 1",
                    [],
                )
            ],
        ),
    ]
}
