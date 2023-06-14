#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated


checkname = "dell_compellent_enclosure"

info = [
    ["1", "1", "", "TYP", "MODEL", "TAG"],
    ["2", "999", "", "TYP", "MODEL", "TAG"],
    ["3", "1", "ATTENTION", "TYP", "MODEL", "TAG"],
    ["4", "999", "ATTENTION", "TYP", "MODEL", "TAG"],
    ["10", "2", "KAPUTT", "TYP", "MODEL", "TAG"],
]

discovery = {"": [("1", {}), ("2", {}), ("3", {}), ("4", {}), ("10", {})]}

checks = {
    "": [
        (
            "1",
            {},
            [
                (0, "Status: UP", []),
                (0, "Model: MODEL, Type: TYP, Service-Tag: TAG", []),
            ],
        ),
        (
            "2",
            {},
            [(3, "Status: unknown[999]", []), (0, "Model: MODEL, Type: TYP, Service-Tag: TAG", [])],
        ),
        (
            "3",
            {},
            [
                (0, "Status: UP", []),
                (0, "Model: MODEL, Type: TYP, Service-Tag: TAG", []),
                (0, "State Message: ATTENTION", []),
            ],
        ),
        (
            "4",
            {},
            [
                (3, "Status: unknown[999]", []),
                (0, "Model: MODEL, Type: TYP, Service-Tag: TAG", []),
                (3, "State Message: ATTENTION", []),
            ],
        ),
        (
            "10",
            {},
            [
                (2, "Status: DOWN", []),
                (0, "Model: MODEL, Type: TYP, Service-Tag: TAG", []),
                (2, "State Message: KAPUTT", []),
            ],
        ),
    ]
}
