#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated

checkname = "scaleio_devices"

info = [
    ["DEVICE", "Foo:"],
    ["ID", "Foo"],
    ["SDS_ID", "123"],
    ["STORAGE_POOL_ID", "abc"],
    ["STATE", "DEVICE_NORMAL"],
    ["ERR_STATE", "NO_ERROR"],
    ["DEVICE", "Bar:"],
    ["ID", "Bar"],
    ["SDS_ID", "123"],
    ["STORAGE_POOL_ID", "def"],
    ["STATE", "DEVICE_NORMAL"],
    ["ERR_STATE", "ERROR"],
    ["DEVICE", "Baz:"],
    ["ID", "Baz"],
    ["SDS_ID", "456"],
    ["STORAGE_POOL_ID", "xyz"],
    ["STATE", "DEVICE_NORMAL"],
    ["ERR_STATE", "NO_ERROR"],
]

discovery = {"": [("123", {}), ("456", {})]}

checks = {
    "": [
        (
            "123",
            {},
            [
                (2, "2 devices, 1 errors (Bar)", []),
                (
                    0,
                    "\nDevice Bar: Error: device normal, State: error (ID: Bar, Storage pool ID: def)",
                    [],
                ),
            ],
        ),
        ("456", {}, [(0, "1 devices, no errors", [])]),
    ]
}
