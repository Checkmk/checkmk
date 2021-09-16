#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, Service, State
from cmk.base.plugins.agent_based.printer_io import (
    check_printer_input,
    check_printer_output,
    discovery_printer_io,
    parse_printer_io,
)


@pytest.mark.parametrize(
    "item, params, info, expected_result",
    [
        (
            "MP TRAY",
            {
                "capacity_levels": (0.0, 0.0),
            },
            [[["1.1", "MP TRAY", "MP TRAY", "0", "0", "0", "0"]]],
            [
                Result(state=State.OK, summary="MP TRAY"),
                Result(state=State.OK, summary="Status: Available and idle"),
                Result(state=State.OK, summary="Alerts: None"),
                Result(state=State.OK, summary="Capacity: 0 unknown"),
            ],
        ),
        (
            "MP TRAY",
            {
                "capacity_levels": (0.0, 0.0),
            },
            [[["1.1", "MP TRAY", "MP TRAY", "0", "0", "0", "-1"]]],
            [
                Result(state=State.OK, summary="MP TRAY"),
                Result(state=State.OK, summary="Status: Available and idle"),
                Result(state=State.OK, summary="Alerts: None"),
            ],
        ),
        (
            "MP TRAY",
            {
                "capacity_levels": (0.0, 0.0),
            },
            [[["1.1", "MP TRAY", "MP TRAY", "96", "0", "0", "0"]]],
            [
                Result(state=State.OK, summary="MP TRAY"),
                Result(state=State.CRIT, summary="Offline"),
                Result(state=State.OK, summary="Transitioning"),
                Result(state=State.OK, summary="Status: Available and idle"),
                Result(state=State.OK, summary="Alerts: None"),
                Result(state=State.OK, summary="Capacity: 0 unknown"),
            ],
        ),
        (
            "MP TRAY",
            {
                "capacity_levels": (0.0, 0.0),
            },
            [[["1.1", "MP TRAY", "MP TRAY", "10", "0", "0", "0"]]],
            [
                Result(state=State.OK, summary="MP TRAY"),
                Result(state=State.OK, summary="Status: Available and standby"),
                Result(state=State.WARN, summary="Alerts: Non-Critical"),
                Result(state=State.OK, summary="Capacity: 0 unknown"),
            ],
        ),
        (
            "MP TRAY",
            {
                "capacity_levels": (0.0, 0.0),
            },
            [[["1.1", "MP TRAY", "MP TRAY", "18", "0", "0", "0"]]],
            [
                Result(state=State.OK, summary="MP TRAY"),
                Result(state=State.OK, summary="Status: Available and standby"),
                Result(state=State.CRIT, summary="Alerts: Critical"),
                Result(state=State.OK, summary="Capacity: 0 unknown"),
            ],
        ),
        (
            "MP TRAY",
            {
                "capacity_levels": (0.0, 0.0),
            },
            [[["1.1", "MP TRAY", "MP TRAY", "0", "8", "-2", "11"]]],
            [
                Result(state=State.OK, summary="MP TRAY"),
                Result(state=State.OK, summary="Status: Available and idle"),
                Result(state=State.OK, summary="Alerts: None"),
                Result(state=State.OK, summary="Capacity: 11 sheets"),
            ],
        ),
        (
            "MP TRAY",
            {
                "capacity_levels": (0.0, 0.0),
            },
            [[["1.1", "MP TRAY", "MP TRAY", "0", "", "-2", "11"]]],
            [
                Result(state=State.OK, summary="MP TRAY"),
                Result(state=State.OK, summary="Status: Available and idle"),
                Result(state=State.OK, summary="Alerts: None"),
                Result(state=State.OK, summary="Capacity: 11"),
            ],
        ),
        (
            "MP TRAY",
            {
                "capacity_levels": (0.0, 0.0),
            },
            [[["1.1", "MP TRAY", "MP TRAY", "0", "18", "15", "-3"]]],
            [
                Result(state=State.OK, summary="MP TRAY"),
                Result(state=State.OK, summary="Status: Available and idle"),
                Result(state=State.OK, summary="Alerts: None"),
                Result(state=State.OK, summary="Maximal capacity: 15 items"),
                Result(state=State.OK, summary="At least one remaining"),
            ],
        ),
        (
            "MP TRAY",
            {
                "capacity_levels": (0.0, 0.0),
            },
            [[["1.1", "MP TRAY", "MP TRAY", "0", "8", "15", "11"]]],
            [
                Result(state=State.OK, summary="MP TRAY"),
                Result(state=State.OK, summary="Status: Available and idle"),
                Result(state=State.OK, summary="Alerts: None"),
                Result(state=State.OK, summary="Maximal capacity: 15 sheets"),
                Result(state=State.OK, summary="Remaining: 73.33%"),
            ],
        ),
        (
            "1",
            {
                "capacity_levels": (80, 20),
            },
            [[["1.1", "", "", "0", "8", "15", "11"]]],
            [
                Result(state=State.OK, summary="Status: Available and idle"),
                Result(state=State.OK, summary="Alerts: None"),
                Result(state=State.OK, summary="Maximal capacity: 15 sheets"),
                Result(
                    state=State.WARN, summary="Remaining: 73.33% (warn/crit below 80.00%/20.00%)"
                ),
            ],
        ),
        (
            "15",
            {
                "capacity_levels": (80, 20),
            },
            [[["1.1", "", "", "0", "8", "15", "11"]]],
            [],
        ),
    ],
)
def test_check_printer_input(item, params, info, expected_result):
    data = parse_printer_io(info)
    result = check_printer_input(item, params, data)
    assert list(result) == expected_result


@pytest.mark.parametrize(
    "item, params, info, expected_result",
    [
        (
            "MP TRAY",
            {
                "capacity_levels": (0.0, 0.0),
            },
            [[["1.1", "MP TRAY", "MP TRAY", "0", "18", "15", "-3"]]],
            [
                Result(state=State.OK, summary="MP TRAY"),
                Result(state=State.OK, summary="Status: Available and idle"),
                Result(state=State.OK, summary="Alerts: None"),
                Result(state=State.OK, summary="Maximal capacity: 15 items"),
                Result(state=State.OK, summary="At least one filled"),
            ],
        ),
        (
            "1",
            {
                "capacity_levels": (70, 80),
            },
            [[["1.1", "", "", "0", "8", "15", "11"]]],
            [
                Result(state=State.OK, summary="Status: Available and idle"),
                Result(state=State.OK, summary="Alerts: None"),
                Result(state=State.OK, summary="Maximal capacity: 15 sheets"),
                Result(state=State.WARN, summary="Filled: 73.33% (warn/crit at 70.00%/80.00%)"),
            ],
        ),
    ],
)
def test_check_priner_output(item, params, info, expected_result):
    data = parse_printer_io(info)
    result = check_printer_output(item, params, data)
    assert list(result) == expected_result


@pytest.mark.parametrize(
    "info, expected_result",
    [
        (
            [
                [
                    ["1.1", "MP TRAY1", "", "0", "8", "15", "11"],
                    ["1.1", "MP TRAY2", "MP TRAY", "0", "8", "0", "11"],
                    ["1.1", "MP TRAY3", "MP TRAY", "3", "8", "5", "11"],
                    ["1.1", "MP TRAY4", "MP TRAY", "6", "8", "6", "11"],
                ],
            ],
            [Service(item="MP TRAY4")],
        )
    ],
)
def test_inventory_printer_io(info, expected_result):
    data = parse_printer_io(info)
    result = discovery_printer_io(data)
    assert list(result) == expected_result
