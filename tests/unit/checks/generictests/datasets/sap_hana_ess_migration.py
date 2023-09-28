#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated
checkname = "sap_hana_ess_migration"

info = [
    ["[[H11", "11]]"],
    [
        "Done",
        "(unknown)",
        "since",
        "2016-02-11",
        "09:14:16.2120000",
        "local",
        "time:2016-02-11",
        "10:14:16.2120000",
    ],
    ["[[H22", "22]]"],
    [
        "Done",
        "(error)",
        "since",
        "2016-02-11",
        "09:14:16.2120000",
        "local",
        "time:2016-02-11",
        "10:14:16.2120000",
    ],
    ["[[H33", "33]]"],
    ["Installing,", "start", "at:", "2017-06-16", "14:53:48.1070000"],
    ["[[H44", "44]]"],
    [
        "Done",
        "(okay)",
        "since",
        "2016-02-12",
        "10:45:51.1630000",
        "local",
        "time:2016-02-12",
        "11:45:51.",
    ],
]

discovery = {"": [("H11 11", {}), ("H22 22", {}), ("H33 33", {}), ("H44 44", {})]}

checks = {
    "": [
        (
            "H11 11",
            {},
            [
                (
                    3,
                    "ESS State: Unknown [Done (unknown) since 2016-02-11 09:14:16.2120000 local time:2016-02-11 10:14:16.2120000] Timestamp: 2016-02-11 09:14:16",
                    [],
                )
            ],
        ),
        ("H22 22", {}, [(2, "ESS State: Done with errors. Timestamp: 2016-02-11 09:14:16", [])]),
        (
            "H33 33",
            {},
            [(1, "ESS State: Installation in progress. Timestamp: 2017-06-16 14:53:48", [])],
        ),
        ("H44 44", {}, [(0, "ESS State: Done without errors. Timestamp: 2016-02-12 10:45:51", [])]),
    ]
}
