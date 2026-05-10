#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import Metric, Result, Service, State
from cmk.plugins.apc.agent_based.apc_rackpdu_power import (
    check_apc_rackpdu_power,
    discover_apc_rackpdu_power,
    parse_apc_rackpdu_power,
)


def test_apc_rackpdu_power_discovery() -> None:
    section = parse_apc_rackpdu_power(
        [
            [["pb-n15-115", "420"]],
            [["1"]],
            [["20", "1", "1", "0"], ["10", "1", "0", "1"], ["9", "1", "0", "2"]],
        ]
    )
    assert section is not None

    discoveries = sorted(discover_apc_rackpdu_power(section), key=lambda s: s.item or "")
    assert discoveries == [
        Service(item="Bank 1"),
        Service(item="Bank 2"),
        Service(item="Device pb-n15-115"),
    ]


def test_apc_rackpdu_power_check_device() -> None:
    section = parse_apc_rackpdu_power(
        [
            [["pb-n15-115", "420"]],
            [["1"]],
            [["20", "1", "1", "0"], ["10", "1", "0", "1"], ["9", "1", "0", "2"]],
        ]
    )
    assert section is not None

    # Device has both power and current (single phase)
    result = list(check_apc_rackpdu_power("Device pb-n15-115", {}, section))
    assert any(isinstance(r, Metric) and r.name == "current" for r in result)
    assert any(isinstance(r, Metric) and r.name == "power" for r in result)
    assert any(
        isinstance(r, Result) and r.state == State.OK and "load normal" in r.summary for r in result
    )
