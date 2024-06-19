#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated

from cmk.plugins.collection.agent_based.lparstat_aix import parse_lparstat_aix

checkname = "lparstat_aix"

parsed = parse_lparstat_aix(
    [
        ["System", "Config", "type=Dedicated", "ent=7.0", "what=ever"],
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
            "#",
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
                (0, "User: 0.20%", [("user", 0.2)]),
                (0, "System: 0.40%", [("system", 0.4)]),
                (0, "Wait: 0%", [("wait", 0.0)]),
                (0, "Total CPU: 0.60%", [("util", 0.6000000000000001, None, None, 0, None)]),
                (0, "Physical CPU consumption: 0.02 CPUs", [("cpu_entitlement_util", 0.02)]),
                (0, "Entitlement: 7.00 CPUs", [("cpu_entitlement", 7.0)]),
            ],
        ),
    ],
}
