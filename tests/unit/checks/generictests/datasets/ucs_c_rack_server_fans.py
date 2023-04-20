#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated


checkname = "ucs_c_rack_server_fans"


info = [
    [
        "equipmentFan",
        "dn sys/rack-unit-1/fan-module-1-1/fan-1",
        "id 1",
        "model ",
        "operability operable",
    ],
    [
        "equipmentFan",
        "dn sys/rack-unit-1/fan-module-1-1/fan-2",
        "id 2",
        "model ",
        "operability operable",
    ],
    [
        "equipmentFan",
        "dn sys/rack-unit-2/fan-module-1-1/fan-1",
        "id 1",
        "model ",
        "operability operable",
    ],
    [
        "equipmentFan",
        "dn sys/rack-unit-2/fan-module-1-1/fan-2",
        "id 2",
        "model ",
        "operability bla",
    ],
    [
        "equipmentFan",
        "dn sys/rack-unit-2/fan-module-1-1/fan-3",
        "id 3",
        "model ",
        "operability blub",
    ],
]


discovery = {
    "": [
        ("Rack Unit 1 Module 1-1 1", {}),
        ("Rack Unit 1 Module 1-1 2", {}),
        ("Rack Unit 2 Module 1-1 1", {}),
        ("Rack Unit 2 Module 1-1 2", {}),
        ("Rack Unit 2 Module 1-1 3", {}),
    ]
}


checks = {
    "": [
        ("Rack Unit 1 Module 1-1 1", {}, [(0, "Operability Status is operable", [])]),
        ("Rack Unit 1 Module 1-1 2", {}, [(0, "Operability Status is operable", [])]),
        ("Rack Unit 2 Module 1-1 1", {}, [(0, "Operability Status is operable", [])]),
        ("Rack Unit 2 Module 1-1 2", {}, [(3, "Unknown Operability Status: bla", [])]),
        ("Rack Unit 2 Module 1-1 3", {}, [(3, "Unknown Operability Status: blub", [])]),
    ]
}
