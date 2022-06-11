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
            "vcsw",
            "phint",
            "%nsp",
            "%utcyc",
        ],
        [
            "-----",
            "-----",
            "------",
            "------",
            "-----",
            "-----",
            "------",
            "-----",
            "-----",
            "-----",
            "------",
        ],
        ["0.2", "0.4", "0.0", "99.3", "0.02", "1.7", "0.0", "215", "3", "101", "0.64"],
    ]
)

discovery = {"": [(None, {})], "cpu_util": [(None, {})]}

checks = {
    "": [
        (
            None,
            (5, 10),
            [
                (0, "Physc: 0.02", [("physc", 0.02, None, None, None, None)]),
                (0, "Entc: 1.7%", [("entc", 1.7, None, None, None, None)]),
                (0, "Lbusy: 0.0", [("lbusy", 0.0, None, None, None, None)]),
                (0, "Vcsw: 215.0", [("vcsw", 215.0, None, None, None, None)]),
                (0, "Phint: 3.0", [("phint", 3.0, None, None, None, None)]),
                (0, "Nsp: 101.0%", [("nsp", 101.0, None, None, None, None)]),
                (0, "Utcyc: 0.64%", [("utcyc", 0.64, None, None, None, None)]),
            ],
        ),
    ],
    "cpu_util": [
        (
            None,
            None,
            [
                (0, "User: 0.2%", [("user", 0.2)]),
                (0, "System: 0.4%", [("system", 0.4)]),
                (0, "Wait: 0%", [("wait", 0.0)]),
                (0, "Total CPU: 0.6%", [("util", 0.6000000000000001, None, None, 0, None)]),
                (0, "Physical CPU consumption: 0.02 CPUs", [("cpu_entitlement_util", 0.02)]),
                (0, "Entitlement: 1.00 CPUs", [("cpu_entitlement", 1.00)]),
            ],
        ),
    ],
}
