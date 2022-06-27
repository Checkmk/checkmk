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
        ["%user", "%wait", "%idle", "physc", "%entc", "lbusy", "vcsw", "phint", "%nsp", "%utcyc"],
        [
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
        ["0.4", "0.0", "99.3", "0.02", "1.7", "0.0", "215", "3", "101", "0.64"],
    ]
)


discovery = {"": [(None, {})], "cpu_util": []}
