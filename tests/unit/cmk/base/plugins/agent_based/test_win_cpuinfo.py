#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

import cmk.base.plugins.agent_based.win_cpuinfo as wci
from cmk.base.plugins.agent_based.agent_based_api.v1 import Attributes


@pytest.fixture(name="section", scope="module")
def _get_section() -> wci._Section:
    return wci.parse_win_cpuinfo(
        [
            ["AddressWidth", " 64"],
            ["Architecture", " 9"],
            ["Caption", " Intel64 Family 6 Model 62 Stepping 4"],
            ["CurrentVoltage", " 33"],
            ["DeviceID", " CPU0"],
            ["L2CacheSize", " 0"],
            ["L3CacheSize", " 0"],
            ["Manufacturer", " GenuineIntel"],
            ["MaxClockSpeed", " 2600"],
            ["Name", " Intel(R) Xeon(R) CPU E5-2650 v2 @ 2.60GHz"],
            ["NumberOfCores", " 4"],
            ["NumberOfLogicalProcessors", " 4"],
            ["Status", " OK"],
            ["AddressWidth", " 64"],
            ["Architecture", " 9"],
            ["Caption", " Intel64 Family 6 Model 62 Stepping 4"],
            ["CurrentVoltage", " 33"],
            ["DeviceID", " CPU1"],
            ["L2CacheSize", " 0"],
            ["L3CacheSize", " 0"],
            ["Manufacturer", " GenuineIntel"],
            ["MaxClockSpeed", " 2600"],
            ["Name", " Intel(R) Xeon(R) CPU E5-2650 v2 @ 2.60GHz"],
            ["NumberOfCores", " 4"],
            ["NumberOfLogicalProcessors", " 4"],
            ["Status", " OK"],
        ]
    )


def test_inventory_win_cpuinfo(section: wci._Section) -> None:
    assert list(wci.inventory_win_cpuinfo(section)) == [
        Attributes(
            path=["hardware", "cpu"],
            inventory_attributes={
                "arch": "x86_64",
                "voltage": 33.0,
                "cache_size": 0,
                "vendor": "intel",
                "max_speed": 2600000000.0,
                "model": "Intel(R) Xeon(R) CPU E5-2650 v2 @ 2.60GHz",
                "cores_per_cpu": 4,
                "threads_per_cpu": 4,
                "cpus": 2,
                "cores": 8,
                "threads": 8,
            },
        ),
    ]
