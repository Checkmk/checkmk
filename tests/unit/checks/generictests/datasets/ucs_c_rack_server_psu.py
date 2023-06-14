#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated

checkname = "ucs_c_rack_server_psu"

info = [
    [
        "equipmentPsu",
        "dn sys/rack-unit-1/psu-1",
        "id 1",
        "model blablub",
        "operability operable",
        "voltage ok",
    ],
    [
        "equipmentPsu",
        "dn sys/rack-unit-1/psu-2",
        "id 2",
        "model blablub",
        "operability removed",
        "voltage ok",
    ],
    [
        "equipmentPsu",
        "dn sys/rack-unit-1/psu-3",
        "id 3",
        "model blablub",
        "operability performance-problem",
        "voltage ok",
    ],
    [
        "equipmentPsu",
        "dn sys/rack-unit-1/psu-4",
        "id 4",
        "model blablub",
        "operability operable",
        "voltage ok",
    ],
    [
        "equipmentPsu",
        "dn sys/rack-unit-2/psu-1",
        "id 1",
        "model blablub",
        "operability operable",
        "voltage lower-non-critical",
    ],
    [
        "equipmentPsu",
        "dn sys/rack-unit-2/psu-2",
        "id 2",
        "model blablub",
        "operability operable",
        "voltage upper-critical",
    ],
    [
        "equipmentPsu",
        "dn sys/rack-unit-2/psu-3",
        "id 3",
        "model blablub",
        "operability operable",
        "voltage unkonwn",
    ],
    [
        "equipmentPsu",
        "dn sys/rack-unit-2/psu-4",
        "id 4",
        "model blablub",
        "operability unknownOperabilityStatus",
        "voltage ok",
    ],
    [
        "equipmentPsu",
        "id sys/rack-unit-2/psu-5",
        "id 5",
        "model blablub",
        "operability operable",
        "voltage unknownVoltageStatus",
    ],
]

discovery = {
    "": [
        ("Rack Unit 1 PSU 1", {}),
        ("Rack Unit 1 PSU 2", {}),
        ("Rack Unit 1 PSU 3", {}),
        ("Rack Unit 1 PSU 4", {}),
        ("Rack Unit 2 PSU 1", {}),
        ("Rack Unit 2 PSU 2", {}),
        ("Rack Unit 2 PSU 3", {}),
        ("Rack Unit 2 PSU 4", {}),
        ("Rack Unit 2 PSU 5", {}),
    ],
    "voltage": [
        ("Rack Unit 1 PSU 1", {}),
        ("Rack Unit 1 PSU 2", {}),
        ("Rack Unit 1 PSU 3", {}),
        ("Rack Unit 1 PSU 4", {}),
        ("Rack Unit 2 PSU 1", {}),
        ("Rack Unit 2 PSU 2", {}),
        ("Rack Unit 2 PSU 3", {}),
        ("Rack Unit 2 PSU 4", {}),
        ("Rack Unit 2 PSU 5", {}),
    ],
}

checks = {
    "": [
        ("Rack Unit 1 PSU 1", {}, [(0, "Status: operable", [])]),
        ("Rack Unit 1 PSU 2", {}, [(1, "Status: removed", [])]),
        ("Rack Unit 1 PSU 3", {}, [(2, "Status: performance-problem", [])]),
        ("Rack Unit 1 PSU 4", {}, [(0, "Status: operable", [])]),
        ("Rack Unit 2 PSU 1", {}, [(0, "Status: operable", [])]),
        ("Rack Unit 2 PSU 2", {}, [(0, "Status: operable", [])]),
        ("Rack Unit 2 PSU 3", {}, [(0, "Status: operable", [])]),
        ("Rack Unit 2 PSU 4", {}, [(3, "Status: unknown[unknownOperabilityStatus]", [])]),
        ("Rack Unit 2 PSU 5", {}, [(0, "Status: operable", [])]),
    ],
    "voltage": [
        ("Rack Unit 1 PSU 1", {}, [(0, "Status: ok", [])]),
        ("Rack Unit 1 PSU 2", {}, [(0, "Status: ok", [])]),
        ("Rack Unit 1 PSU 3", {}, [(0, "Status: ok", [])]),
        ("Rack Unit 1 PSU 4", {}, [(0, "Status: ok", [])]),
        ("Rack Unit 2 PSU 1", {}, [(1, "Status: lower-non-critical", [])]),
        ("Rack Unit 2 PSU 2", {}, [(2, "Status: upper-critical", [])]),
        ("Rack Unit 2 PSU 3", {}, [(3, "Status: unknown[unkonwn]", [])]),
        ("Rack Unit 2 PSU 4", {}, [(0, "Status: ok", [])]),
        ("Rack Unit 2 PSU 5", {}, [(3, "Status: unknown[unknownVoltageStatus]", [])]),
    ],
}
