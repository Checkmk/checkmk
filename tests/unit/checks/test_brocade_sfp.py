#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from tests.testlib import Check


@pytest.mark.parametrize(
    "item, params, parsed, expected_result",
    [
        (
            "00 ISL B001FCSW1P00",
            {"voltage": (0.0, 0.0, 3.3, 3.5)},
            [
                "",
                {
                    "port_name": "B001FCSW1P00",
                    "temp": 41,
                    "phystate": 6,
                    "opstate": 1,
                    "admstate": 1,
                    "voltage": 3.3075,
                    "current": 0.045380000000000004,
                    "rx_power": -3.0,
                    "tx_power": 0.5,
                    "is_isl": True,
                },
            ],
            [
                (0, "Rx: -3.00 dBm", [("input_signal_power_dbm", -3.0, None, None)]),
                (0, "Tx: 0.50 dBm", [("output_signal_power_dbm", 0.5, None, None)]),
                (0, "Current: 0.05 A", [("current", 0.045380000000000004, None, None)]),
                (
                    1,
                    "Voltage: 3.31 V (warn/crit at 3.30 V/3.50 V)",
                    [("voltage", 3.3075, 3.3, 3.5)],
                ),
            ],
        )
    ],
)
def test_check_brocade_sfp(item, params, parsed, expected_result):
    result = Check("brocade_sfp").run_check(item, params, parsed)
    assert list(result) == expected_result
