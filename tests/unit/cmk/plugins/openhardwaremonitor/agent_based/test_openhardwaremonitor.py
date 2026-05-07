#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from cmk.agent_based.v2 import Metric, Result, Service, State, StringTable
from cmk.plugins.openhardwaremonitor.agent_based.openhardwaremonitor import (
    check_openhardwaremonitor_clock,
    discover_openhardwaremonitor,
    parse_openhardwaremonitor,
)

_STRING_TABLE: StringTable = [
    ["Index", "Name", "Parent", "SensorType", "Value"],
    ["0", "Temperature", "/hdd/0", "Temperature", "28.000000"],
    ["0", "System Fan", "/lpc/w83627dhgp", "Fan", "1506.696411"],
    ["1", "CPU Fan", "/lpc/w83627dhgp", "Fan", "2518.656738"],
    ["1", "CPU Cores", "/intelcpu/0", "Power", "1.651155"],
    ["0", "CPU Core #1", "/intelcpu/0", "Temperature", "28.000000"],
    ["0", "Remaining Life", "/hdd/0", "Level", "98.000000"],
    ["1", "CPU Core #1", "/intelcpu/0", "Clock", "1297.013062"],
    ["1", "CPU Core #1", "/intelcpu/0", "Load", "12.307692"],
    ["2", "CPU Core #2", "/intelcpu/0", "Clock", "1297.013062"],
    ["0", "Memory", "/ram", "Load", "61.928921"],
    ["2", "CPU Graphics", "/intelcpu/0", "Power", "0.040867"],
    ["1", "CPU Core #2", "/intelcpu/0", "Temperature", "29.000000"],
    ["3", "CPU DRAM", "/intelcpu/0", "Power", "1.188020"],
    ["2", "CPU Core #3", "/intelcpu/0", "Temperature", "31.000000"],
    ["1", "Host Writes to Controller", "/hdd/0", "Data", "1589.000000"],
    ["2", "Host Reads", "/hdd/0", "Data", "1366.000000"],
    ["4", "CPU Core #4", "/intelcpu/0", "Load", "6.153846"],
    ["3", "CPU Core #3", "/intelcpu/0", "Clock", "1297.013062"],
    ["3", "CPU Core #3", "/intelcpu/0", "Load", "18.461536"],
    ["4", "CPU Core #4", "/intelcpu/0", "Clock", "1297.013062"],
    ["1", "Available Memory", "/ram", "Data", "3.011536"],
    ["2", "CPU Core #2", "/intelcpu/0", "Load", "15.384615"],
    ["0", "Controller Writes to NAND", "/hdd/0", "Data", "3371.000000"],
    ["1", "Write Amplification", "/hdd/0", "Factor", "2.121460"],
    ["0", "CPU Total", "/intelcpu/0", "Load", "13.076920"],
    ["0", "Bus Speed", "/intelcpu/0", "Clock", "99.770233"],
    ["0", "Used Memory", "/ram", "Data", "4.898762"],
    ["3", "CPU Core #4", "/intelcpu/0", "Temperature", "27.000000"],
    ["4", "CPU Package", "/intelcpu/0", "Temperature", "31.000000"],
    ["0", "Used Space", "/hdd/0", "Load", "72.429222"],
]


def test_discover_openhardwaremonitor() -> None:
    parsed = parse_openhardwaremonitor(_STRING_TABLE)
    assert sorted(discover_openhardwaremonitor(parsed), key=lambda s: s.item or "") == [
        Service(item="cpu0 Bus Speed"),
        Service(item="cpu0 Core #1"),
        Service(item="cpu0 Core #2"),
        Service(item="cpu0 Core #3"),
        Service(item="cpu0 Core #4"),
    ]


@pytest.mark.parametrize(
    "item, expected_summary, expected_value",
    [
        ("cpu0 Bus Speed", "99.8 MHz", 99.770233),
        ("cpu0 Core #1", "1297.0 MHz", 1297.013062),
        ("cpu0 Core #2", "1297.0 MHz", 1297.013062),
        ("cpu0 Core #3", "1297.0 MHz", 1297.013062),
        ("cpu0 Core #4", "1297.0 MHz", 1297.013062),
    ],
)
def test_check_openhardwaremonitor(item: str, expected_summary: str, expected_value: float) -> None:
    parsed = parse_openhardwaremonitor(_STRING_TABLE)
    params: Mapping[str, Sequence[float]] = {}
    result = list(check_openhardwaremonitor_clock(item, params, parsed))
    assert result == [
        Result(state=State.OK, summary=expected_summary),
        Metric("clock", expected_value),
    ]


def test_check_openhardwaremonitor_unknown_item() -> None:
    parsed = parse_openhardwaremonitor(_STRING_TABLE)
    assert list(check_openhardwaremonitor_clock("does-not-exist", {}, parsed)) == []


def _expected_results_unused(_x: Any) -> None:
    pass
