#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# type: ignore

from cmk.base.plugins.agent_based.lparstat_aix import parse_lparstat_aix

checkname = "lparstat_aix"


parsed = parse_lparstat_aix(
    [
        [
            "System",
            "configuration:",
            "type=Shared",
            "mode=Uncapped",
            "smt=4",
            "lcpu=8",
            "mem=16384MB",
            "psize=4",
            "ent=1.00",
        ],
        [
            "%user",
            "%sys",
            "%wait",
            "%idle",
            "physc",
            "%entc",
            "lbusy",
            "app",
            "vcsw",
            "phint",
            "%nsp",
        ],
        ["this line is ignored"],
        ["0.2", "1.2", "0.2", "98.6", "0.02", "9.3", "0.1", "519", "0", "101", "0.00"],
    ]
)

discovery = {"": [(None, {})], "cpu_util": [(None, {})]}

checks = {
    "": [
        (
            None,
            None,
            [
                (0, "Physc: 0.02", [("physc", 0.02, None, None, None, None)]),
                (0, "Entc: 9.3%", [("entc", 9.3, None, None, None, None)]),
                (0, "Lbusy: 0.1", [("lbusy", 0.1, None, None, None, None)]),
                (0, "App: 519.0", [("app", 519.0, None, None, None, None)]),
                (0, "Vcsw: 0.0", [("vcsw", 0.0, None, None, None, None)]),
                (0, "Phint: 101.0", [("phint", 101.0, None, None, None, None)]),
                (0, "Nsp: 0.0%", [("nsp", 0.0, None, None, None, None)]),
            ],
        ),
    ],
    "cpu_util": [
        (
            None,
            None,
            [
                (0, "User: 0.20%", [("user", 0.2)]),
                (0, "System: 1.20%", [("system", 1.2)]),
                (0, "Wait: 0.20%", [("wait", 0.2)]),
                (0, "Total CPU: 1.60%", [("util", 1.5999999999999999, None, None, 0, None)]),
                (0, "Physical CPU consumption: 0.02 CPUs", [("cpu_entitlement_util", 0.02)]),
                (0, "Entitlement: 1.00 CPUs", [("cpu_entitlement", 1.0)]),
            ],
        ),
        (
            None,
            (0.1, 0.3),
            [
                (0, "User: 0.20%", [("user", 0.2)]),
                (0, "System: 1.20%", [("system", 1.2)]),
                (1, "Wait: 0.20% (warn/crit at 0.10%/0.30%)", [("wait", 0.2, 0.1, 0.3)]),
                (0, "Total CPU: 1.60%", [("util", 1.5999999999999999, None, None, 0, None)]),
                (0, "Physical CPU consumption: 0.02 CPUs", [("cpu_entitlement_util", 0.02)]),
                (0, "Entitlement: 1.00 CPUs", [("cpu_entitlement", 1.0)]),
            ],
        ),
        (
            None,
            {"util": (0.5, 1.3)},
            [
                (0, "User: 0.20%", [("user", 0.2)]),
                (0, "System: 1.20%", [("system", 1.2)]),
                (0, "Wait: 0.20%", [("wait", 0.2)]),
                (
                    2,
                    "Total CPU: 1.60% (warn/crit at 0.50%/1.30%)",
                    [("util", 1.5999999999999999, 0.5, 1.3, 0, None)],
                ),
                (0, "Physical CPU consumption: 0.02 CPUs", [("cpu_entitlement_util", 0.02)]),
                (0, "Entitlement: 1.00 CPUs", [("cpu_entitlement", 1.0)]),
            ],
        ),
    ],
}
