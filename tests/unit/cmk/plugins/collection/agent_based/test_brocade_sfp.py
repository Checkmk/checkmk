#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from cmk.agent_based.v2 import Metric, Result, State
from cmk.plugins.collection.agent_based import brocade_sfp


@pytest.mark.parametrize(
    "item, params, section, expected_result",
    [
        (
            "00 ISL B001FCSW1P00",
            {"voltage": (0.0, 0.0, 3.3, 3.5)},
            {
                1: {
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
            },
            [
                Result(state=State.OK, summary="Rx: -3.00 dBm"),
                Metric("input_signal_power_dbm", -3.0),
                Result(state=State.OK, summary="Tx: 0.50 dBm"),
                Metric("output_signal_power_dbm", 0.5),
                Result(state=State.OK, summary="Current: 0.05 A"),
                Metric("current", 0.045380000000000004),
                Result(state=State.WARN, summary="Voltage: 3.31 V (warn/crit at 3.30 V/3.50 V)"),
                Metric("voltage", 3.3075, levels=(3.3, 3.5)),
            ],
        )
    ],
)
def test_check_brocade_sfp(
    item: str,
    params: Mapping[str, Any],
    section: brocade_sfp.Section,
    expected_result: Sequence[Result | Metric],
) -> None:
    assert list(brocade_sfp.check_brocade_sfp(item, params, section)) == expected_result
