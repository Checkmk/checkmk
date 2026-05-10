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


def test_apc_rackpdu_power_1() -> None:
    raw_data = [
        [["luz0010x", "0"]],
        [["3"]],
        [["0", "1", "1", "0"], ["0", "1", "2", "0"], ["0", "1", "3", "0"]],
    ]

    parsed_section = parse_apc_rackpdu_power(raw_data)
    assert parsed_section is not None

    discovery_result = sorted(
        discover_apc_rackpdu_power(parsed_section), key=lambda s: s.item or ""
    )
    assert discovery_result == [
        Service(item="Device luz0010x"),
        Service(item="Phase 1"),
        Service(item="Phase 2"),
        Service(item="Phase 3"),
    ]

    # Test check for device (has power but no current)
    device_result = list(check_apc_rackpdu_power("Device luz0010x", {}, parsed_section))
    assert any(isinstance(r, Result) for r in device_result)
    assert any(isinstance(r, Metric) and r.name == "power" for r in device_result)

    # Test check for phase (has current but no power)
    phase_result = list(check_apc_rackpdu_power("Phase 1", {}, parsed_section))
    assert any(isinstance(r, Result) for r in phase_result)
    assert any(isinstance(r, Metric) and r.name == "current" for r in phase_result)
    assert any(
        isinstance(r, Result) and r.state == State.OK and "load normal" in r.summary
        for r in phase_result
    )
