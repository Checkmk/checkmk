#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.base.plugins.agent_based.juniper_cpu_util import parse_juniper_cpu_util


def test_parse_juniper_cpu_util():
    assert parse_juniper_cpu_util(
        [
            ["midplane", "0"],
            ["Bottom Tray Fan 1", "0"],
            ["FPC: EX9200-40FE @ 0/*/*", "42"],
            ["Routing Engine 0", "5"],
        ]
    ) == {
        "Bottom Tray Fan 1": 0,
        "FPC: EX9200-40FE 0": 42,
        "Routing Engine 0": 5,
        "midplane": 0,
    }
