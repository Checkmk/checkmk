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
        [["pb-n15-115", "420"]],
        [["1"]],
        [["20", "1", "1", "0"], ["10", "1", "0", "1"], ["9", "1", "0", "2"]],
    ],
)

discovery = {"": [("Bank 1", {}), ("Bank 2", {}), ("Device pb-n15-115", {})]}

checks = {
    "": [
        (
            "Bank 1",
            {},
            [
                (0, "Current: 1.0 A", [("current", 1.0, None, None, None, None)]),
                (0, "load normal", []),
            ],
        ),
        (
            "Bank 2",
            {},
            [
                (0, "Current: 0.9 A", [("current", 0.9, None, None, None, None)]),
                (0, "load normal", []),
            ],
        ),
        (
            "Device pb-n15-115",
            {},
            [
                (0, "Current: 2.0 A", [("current", 2.0, None, None, None, None)]),
                (0, "load normal", []),
                (0, "Power: 420.0 W", [("power", 420.0, None, None, None, None)]),
            ],
        ),
    ]
}
