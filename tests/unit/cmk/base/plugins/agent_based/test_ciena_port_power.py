#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Sequence

import pytest

from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, State
from cmk.base.plugins.agent_based.ciena_port_power import (
    check_ciena_port_power,
    inf,
    PortPower,
    PowerReading,
)


@pytest.mark.parametrize(
    "port_power, expected",
    [
        pytest.param(
            PortPower(
                receive=PowerReading(
                    power=-2.0,
                    treshold_upper=-1.0,
                    treshold_lower=-3.0,
                ),
                transmit=PowerReading(
                    power=-5.0,
                    treshold_upper=2.0,
                    treshold_lower=-10.0,
                ),
            ),
            [
                Result(state=State.OK, summary="Receive: -2.000 dBm"),
                Metric("input_signal_power_dbm", -2.0, levels=(-1.0, -1.0)),
                Result(state=State.OK, notice="Receive: crit above -1.0, crit below -3.0"),
                Result(state=State.OK, summary="Transmit: -5.000 dBm"),
                Metric("output_signal_power_dbm", -5.0, levels=(2.0, 2.0)),
                Result(state=State.OK, notice="Transmit: crit above 2.0, crit below -10.0"),
            ],
            id="Port with ok readings.",
        ),
        pytest.param(
            PortPower(
                receive=PowerReading(
                    power=0.0,
                    treshold_upper=-1.0,
                    treshold_lower=-3.0,
                ),
                transmit=PowerReading(
                    power=-11.0,
                    treshold_upper=2.0,
                    treshold_lower=-10.0,
                ),
            ),
            [
                Result(
                    state=State.CRIT,
                    summary="Receive: 0.000 dBm (warn/crit at -1.000 dBm/-1.000 dBm)",
                ),
                Metric("input_signal_power_dbm", 0.0, levels=(-1.0, -1.0)),
                Result(state=State.OK, notice="Receive: crit above -1.0, crit below -3.0"),
                Result(
                    state=State.CRIT,
                    summary="Transmit: -11.000 dBm (warn/crit below -10.000 dBm/-10.000 dBm)",
                ),
                Metric("output_signal_power_dbm", -11.0, levels=(2.0, 2.0)),
                Result(state=State.OK, notice="Transmit: crit above 2.0, crit below -10.0"),
            ],
            id="Port with critical readings. Receive is above, transmit is below.",
        ),
        pytest.param(
            PortPower(
                receive=PowerReading(
                    power=-inf,
                    treshold_upper=-inf,
                    treshold_lower=-inf,
                ),
                transmit=PowerReading(
                    power=-inf,
                    treshold_upper=-inf,
                    treshold_lower=-inf,
                ),
            ),
            [
                Result(state=State.OK, summary="Received signal power is 0 watt"),
                Result(state=State.OK, summary="Transmitted signal power is 0 watt"),
            ],
            id="Microwatt reading set to zero.",
        ),
    ],
)
def test_check_kube_pod_info(port_power: PortPower, expected: Sequence[Result]) -> None:
    assert list(check_ciena_port_power("1", {"1": port_power})) == expected
