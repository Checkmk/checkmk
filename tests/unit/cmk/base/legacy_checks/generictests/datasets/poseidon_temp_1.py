#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated

checkname = "poseidon_temp"

info = [["Bezeichnung Sensor 1", "1", "16.8 C"]]

discovery = {"": [("Bezeichnung Sensor 1", {})]}

checks = {
    "": [
        (
            "Bezeichnung Sensor 1",
            {},
            [
                (0, "Sensor Bezeichnung Sensor 1, State normal", []),
                (0, "16.8 \xb0C", [("temp", 16.8, None, None, None, None)]),
            ],
        )
    ]
}
