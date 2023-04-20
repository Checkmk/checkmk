#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated

checkname = "k8s_conditions"

info = [
    [
        '{"DiskPressure": "False", "OutOfDisk": "False", "MemoryPressure": "False", "Ready": "False", "NetworkUnavailable": "False", "KernelDeadlock": "True"}'
    ]
]

discovery = {
    "": [
        ("DiskPressure", {}),
        ("KernelDeadlock", {}),
        ("MemoryPressure", {}),
        ("NetworkUnavailable", {}),
        ("OutOfDisk", {}),
        ("Ready", {}),
    ]
}

checks = {
    "": [
        ("DiskPressure", {}, [(0, "False", [])]),
        ("KernelDeadlock", {}, [(2, "True", [])]),
        ("MemoryPressure", {}, [(0, "False", [])]),
        ("NetworkUnavailable", {}, [(0, "False", [])]),
        ("OutOfDisk", {}, [(0, "False", [])]),
        ("Ready", {}, [(2, "False", [])]),
    ]
}
