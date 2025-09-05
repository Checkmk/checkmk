#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated

from cmk.plugins.collection.agent_based.apc_rackpdu_power import parse_apc_rackpdu_power

checkname = "apc_rackpdu_power"

parsed = parse_apc_rackpdu_power(
    [
        [["luz0010x", "0"]],
        [["3"]],
        [["0", "1", "1", "0"], ["0", "1", "2", "0"], ["0", "1", "3", "0"]],
    ],
)

discovery = {"": [("Device luz0010x", {}), ("Phase 1", {}), ("Phase 2", {}), ("Phase 3", {})]}

checks = {
    "": [
        ("Device luz0010x", {}, [(0, "Power: 0.0 W", [("power", 0.0, None, None, None, None)])]),
        (
            "Phase 1",
            {},
            [
                (0, "Current: 0.0 A", [("current", 0.0, None, None, None, None)]),
                (0, "load normal", []),
            ],
        ),
        (
            "Phase 2",
            {},
            [
                (0, "Current: 0.0 A", [("current", 0.0, None, None, None, None)]),
                (0, "load normal", []),
            ],
        ),
        (
            "Phase 3",
            {},
            [
                (0, "Current: 0.0 A", [("current", 0.0, None, None, None, None)]),
                (0, "load normal", []),
            ],
        ),
    ]
}
