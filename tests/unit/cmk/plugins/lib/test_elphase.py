#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import Metric, Result, State
from cmk.plugins.lib.elphase import check_elphase


def test_check_elphase() -> None:
    assert list(
        check_elphase(
            {
                "map_device_states": [("1", 2)],
                "voltage": (210.0, 200.0),
                "current": (10.0, 20.0),
                "frequency": (45.0, 35.0, 47.0, 55.0),
                "differential_current_ac": (15.0, 17.0),
            },
            {
                "name": "Phase 1",
                "type": "UPS Inc. model 123",
                "device_state": (1, "warning"),
                "voltage": 250.2,
                "current": (13.1, (1, "High current")),
                "output_load": 83.0,
                "power": 34.2,
                "appower": 78.0,
                "energy": 66.1,
                "frequency": 50.0,
                "differential_current_ac": 20.0,
                "differential_current_dc": 10.0,
            },
        )
    ) == [
        Result(state=State.OK, summary="Name: Phase 1"),
        Result(state=State.OK, summary="Type: UPS Inc. model 123"),
        Result(state=State.OK, summary="Device status: warning(1)"),
        Result(state=State.OK, summary="Voltage: 250.2 V"),
        Metric("voltage", 250.2),
        Result(state=State.WARN, summary="Current: 13.1 A (warn/crit at 10.0 A/20.0 A)"),
        Metric("current", 13.1, levels=(10.0, 20.0)),
        Result(state=State.WARN, summary="High current"),
        Result(state=State.OK, summary="Load: 83.00%"),
        Metric("output_load", 83.0),
        Result(state=State.OK, summary="Power: 34.2 W"),
        Metric("power", 34.2),
        Result(state=State.OK, summary="Apparent Power: 78.0 VA"),
        Metric("appower", 78.0),
        Result(state=State.OK, summary="Energy: 66.1 Wh"),
        Metric("energy", 66.1),
        Result(state=State.CRIT, summary="Frequency: 50.0 hz (warn/crit at 45.0 hz/35.0 hz)"),
        Metric("frequency", 50.0, levels=(45.0, 35.0)),
        Result(
            state=State.CRIT,
            summary="Differential current AC: 20.0 mA (warn/crit at 15.0 mA/17.0 mA)",
        ),
        Metric("differential_current_ac", 0.02, levels=(0.015, 0.017)),
        Result(state=State.OK, summary="Differential current DC: 10.0 mA"),
        Metric("differential_current_dc", 0.01),
    ]
