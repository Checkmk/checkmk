#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import Metric, Result, Service, State
from cmk.plugins.ups.agent_based.ups_socomec_outphase import (
    check_ups_socomec_outphase,
    discover_ups_socomec_outphase,
    parse_ups_socomec_outphase,
)

_PARAMS = {"voltage": (210, 200), "output_load": (80, 90)}


def test_discover_ups_socomec_outphase() -> None:
    section = parse_ups_socomec_outphase([["1", "2300", "100", "50"]])
    assert list(discover_ups_socomec_outphase(section)) == [Service(item="Phase 1")]


def test_check_ups_socomec_outphase() -> None:
    section = parse_ups_socomec_outphase([["1", "2300", "100", "50"]])
    assert list(check_ups_socomec_outphase("Phase 1", _PARAMS, section)) == [
        Result(state=State.OK, summary="Voltage: 230.0 V"),
        Metric("voltage", 230.0),
        Result(state=State.OK, summary="Current: 10.0 A"),
        Metric("current", 10.0),
        Result(state=State.OK, summary="Load: 50.00%"),
        Metric("output_load", 50.0, levels=(80.0, 90.0)),
    ]


def test_check_ups_socomec_outphase_legacy_item_name() -> None:
    # items discovered before 1.2.7 were bare phase indices
    section = parse_ups_socomec_outphase([["1", "2300", "100", "50"]])
    assert list(check_ups_socomec_outphase("1", _PARAMS, section))[0] == Result(
        state=State.OK, summary="Voltage: 230.0 V"
    )
