#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated


checkname = "ibm_svc_host"


info = [
    ["0", "h_esx01", "2", "4", "degraded"],
    ["1", "host206", "2", "2", "online"],
    ["2", "host105", "2", "2", "online"],
    ["3", "host106", "2", "2", "online"],
]


discovery = {"": [(None, {})]}


checks = {
    "": [
        (
            None,
            {},
            [
                (0, "3 active", []),
                (0, "0 inactive", [("inactive", 0, None, None, None, None)]),
                (0, "1 degraded", [("degraded", 1, None, None, None, None)]),
                (0, "0 offline", [("offline", 0, None, None, None, None)]),
                (0, "0 other", [("other", 0, None, None, None, None)]),
            ],
        )
    ]
}
