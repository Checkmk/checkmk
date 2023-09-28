#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated

checkname = "jolokia_jvm_runtime"

freeze_time = "2019-10-11 08:32:51"

info = [
    ["MyJIRA", "java.lang:type=Runtime/Uptime,Name", '{"Uptime": 34502762, "Name": "1020@jira"}']
]

discovery = {"": [("MyJIRA", {})]}

checks = {
    "": [
        (
            "MyJIRA",
            {},
            [
                (
                    0,
                    "Up since Fri Oct 11 00:57:48 2019, uptime: 9:35:02",
                    [("uptime", 34502.762, None, None, None, None)],
                )
            ],
        )
    ]
}
