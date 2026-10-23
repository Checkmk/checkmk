#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import Metric, Result, State
from cmk.plugins.apc.agent_based.apc_inrow_fanspeed import (
    check_apc_inrow_fanspeed,
    parse_apc_inrow_fanspeed,
)


def test_air_irrc_fanspeed_is_tenths_of_a_percent() -> None:
    assert parse_apc_inrow_fanspeed([[["518"]], []]) == 51.8


def test_cooling_unit_fanspeed() -> None:
    assert (
        parse_apc_inrow_fanspeed(
            [[], [["Airflow", "412", "L/s", "1"], ["Fan Speed", "30", "%", "1"]]]
        )
        == 30.0
    )


def test_check_reports_percent_and_metric() -> None:
    assert list(check_apc_inrow_fanspeed(51.8)) == [
        Result(state=State.OK, summary="Current: 51.80%"),
        Metric("fan_perc", 51.8),
    ]
