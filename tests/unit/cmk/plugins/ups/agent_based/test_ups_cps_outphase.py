#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.agent_based.v2 import Metric, Result, Service, State, StringTable
from cmk.plugins.ups.agent_based.ups_cps_outphase import (
    check_ups_cps_outphase,
    discover_ups_cps_outphase,
    parse_ups_cps_outphase,
)


@pytest.mark.parametrize(
    "string_table, expected",
    [
        ([["2300", "500", "50", "100"]], [Service(item="1")]),
        ([], []),
    ],
)
def test_discover_ups_cps_outphase(string_table: StringTable, expected: list[Service]) -> None:
    assert list(discover_ups_cps_outphase(parse_ups_cps_outphase(string_table) or {})) == expected


def test_check_ups_cps_outphase() -> None:
    section = parse_ups_cps_outphase([["2300", "500", "50", "100"]])
    assert section
    assert list(check_ups_cps_outphase("1", {}, section)) == [
        Result(state=State.OK, summary="Voltage: 230.0 V"),
        Metric("voltage", 230.0),
        Result(state=State.OK, summary="Current: 10.0 A"),
        Metric("current", 10.0),
        Result(state=State.OK, summary="Load: 50.00%"),
        Metric("output_load", 50.0),
        Result(state=State.OK, summary="Frequency: 50.0 Hz"),
        Metric("frequency", 50.0),
    ]


def test_check_ups_cps_outphase_missing_item() -> None:
    section = parse_ups_cps_outphase([["2300", "500", "50", "100"]])
    assert section
    assert list(check_ups_cps_outphase("2", {}, section)) == []
