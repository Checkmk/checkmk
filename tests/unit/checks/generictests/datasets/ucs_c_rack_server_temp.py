#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated

checkname = "ucs_c_rack_server_temp"

info = [
    [
        "processorEnvStats",
        "dn sys/rack-unit-1/board/cpu-1/env-stats",
        "id 1",
        "description blalub",
        "temperature 58.4",
    ],
    [
        "processorEnvStats",
        "dn sys/rack-unit-1/board/cpu-2/env-stats",
        "id 2",
        "description blalub",
        "temperature 60.4",
    ],
    [
        "memoryUnitEnvStats",
        "dn sys/rack-unit-1/board/memarray-1/mem-1/dimm-env-stats",
        "id 1",
        "description blalub",
        "temperature 40.4",
    ],
    [
        "memoryUnitEnvStats",
        "dn sys/rack-unit-1/board/memarray-1/mem-2/dimm-env-stats",
        "id 2",
        "description blalub",
        "temperature 61.4",
    ],
    [
        "computeRackUnitMbTempStats",
        "dn sys/rack-unit-1/board/temp-stats",
        "ambientTemp 40.0",
        "frontTemp 50.0",
        "ioh1Temp 50.0",
        "ioh2Temp 50.0",
        "rearTemp 50.0",
    ],
    [
        "computeRackUnitMbTempStats",
        "dn sys/rack-unit-2/board/temp-stats",
        "ambientTemp 60.0",
        "frontTemp 50.0",
        "ioh1Temp 50.0",
        "ioh2Temp 50.0",
        "rearTemp 50.0",
    ],
]

discovery = {
    "": [
        ("Rack Unit 1 CPU 1", {}),
        ("Rack Unit 1 CPU 2", {}),
        ("Rack Unit 1 Memory Array 1 Memory DIMM 1", {}),
        ("Rack Unit 1 Memory Array 1 Memory DIMM 2", {}),
        ("Rack Unit 1 Motherboard", {}),
        ("Rack Unit 2 Motherboard", {}),
    ]
}

checks = {
    "": [
        ("Rack Unit 1 CPU 1", {}, [(0, "58.4 \xb0C", [("temp", 58.4, None, None, None, None)])]),
        ("Rack Unit 1 CPU 2", {}, [(0, "60.4 \xb0C", [("temp", 60.4, None, None, None, None)])]),
        (
            "Rack Unit 1 Memory Array 1 Memory DIMM 1",
            {},
            [(0, "40.4 \xb0C", [("temp", 40.4, None, None, None, None)])],
        ),
        (
            "Rack Unit 1 Memory Array 1 Memory DIMM 2",
            {},
            [(0, "61.4 \xb0C", [("temp", 61.4, None, None, None, None)])],
        ),
        (
            "Rack Unit 1 Motherboard",
            {},
            [(0, "50.0 \xb0C", [("temp", 50.0, None, None, None, None)])],
        ),
        (
            "Rack Unit 2 Motherboard",
            {},
            [(0, "50.0 \xb0C", [("temp", 50.0, None, None, None, None)])],
        ),
    ]
}
