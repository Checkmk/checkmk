#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated


checkname = "dell_compellent_controller"

info = [
    ["1", "1", "Foo", "1.2.3.4", "Model"],
    ["2", "999", "Bar", "5.6.7.8", "Model"],
    ["10", "2", "Baz", "1.3.5.7", "Model"],
]

discovery = {"": [("1", {}), ("2", {}), ("10", {})]}

checks = {
    "": [
        (
            "1",
            {},
            [
                (0, "Status: UP", []),
                (0, "Model: Model, Name: Foo, Address: 1.2.3.4", []),
            ],
        ),
        (
            "2",
            {},
            [
                (3, "Status: unknown[999]", []),
                (0, "Model: Model, Name: Bar, Address: 5.6.7.8", []),
            ],
        ),
        (
            "10",
            {},
            [
                (2, "Status: DOWN", []),
                (0, "Model: Model, Name: Baz, Address: 1.3.5.7", []),
            ],
        ),
    ]
}
