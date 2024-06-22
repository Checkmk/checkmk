#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code=var-annotated

from cmk.plugins.collection.agent_based.lparstat_aix import parse_lparstat_aix

checkname = "lparstat_aix"


parsed = parse_lparstat_aix(
    [
        [
            "System",
            "configuration:",
            "type=Dedicated",
            "mode=Capped",
            "smt=4",
            "lcpu=4",
            "mem=16384MB",
        ],
        ["%user", "%sys", "%wait", "%idle"],
        ["-----", "-----", "------", "------"],
        ["0.1", "58.8", "0.0", "41.1"],
    ]
)

discovery = {"": [], "cpu_util": [(None, {})]}


checks = {
    "cpu_util": [
        (
            None,
            {},
            [
                (0, "User: 0.10%", [("user", 0.1, None, None, None, None)]),
                (0, "System: 58.80%", [("system", 58.8, None, None, None, None)]),
                (0, "Wait: 0%", [("wait", 0.0, None, None, None, None)]),
                (0, "Total CPU: 58.90%", [("util", 58.9, None, None, 0, None)]),
            ],
        )
    ]
}
