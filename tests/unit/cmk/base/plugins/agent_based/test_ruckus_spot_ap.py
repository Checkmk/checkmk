#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from typing import Final

from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, Service, State
from cmk.base.plugins.agent_based.ruckus_spot_ap import (
    check_ruckus_spot_ap,
    discover_ruckus_spot_ap,
    parse_ruckus_spot_ap,
)

# reverse engineered from the plugin. No idea if this is correct.
STRING_TABLE: Final = [
    [
        json.dumps(
            [
                {
                    "band": 1,
                    "access_points": [
                        {"name": "Stuart", "status": 2},
                        {"name": "Dave", "status": 1},
                    ],
                },
                {
                    "band": 2,
                    "access_points": [
                        {"name": "Kevin", "status": 0},
                        {"name": "Bob", "status": 1},
                    ],
                },
            ],
        ),
    ]
]


def test_discovery() -> None:
    section = parse_ruckus_spot_ap(STRING_TABLE)
    assert [*discover_ruckus_spot_ap(section)] == [
        Service(item="2.4 GHz"),
        Service(item="5 GHz"),
    ]


def test_check_no_data() -> None:
    assert not [*check_ruckus_spot_ap("2.4 GHz", {}, {})]


def test_check() -> None:
    section = parse_ruckus_spot_ap(STRING_TABLE)
    params = {"levels_drifted": (0, 1), "levels_not_responding": (2, 3)}
    assert [*check_ruckus_spot_ap("5 GHz", params, section)] == [
        Result(state=State.OK, summary="Devices: 2"),
        Metric("ap_devices_total", 2.0),
        Result(state=State.WARN, summary="Drifted: 0 (warn/crit at 0/1)"),
        Metric("ap_devices_drifted", 0.0, levels=(0.0, 1.0)),
        Result(state=State.OK, notice="Not responding: 1"),
        Metric("ap_devices_not_responding", 1.0, levels=(2.0, 3.0)),
    ]
