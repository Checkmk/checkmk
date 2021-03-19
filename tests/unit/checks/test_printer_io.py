#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from testlib import Check


@pytest.mark.parametrize("item, params, info, expected_result", [
    (
        "MP TRAY",
        {
            "capacity_levels": (0.0, 0.0),
        },
        [["1.1", "MP TRAY", "MP TRAY", "0", "0", "0", "0"]],
        [
            (0, "MP TRAY"),
            (0, "Status: Available and idle"),
            (False, "Alerts: None"),
            (0, 'Capacity: 0 unknown'),
        ],
    ),
    (
        "MP TRAY",
        {
            "capacity_levels": (0.0, 0.0),
        },
        [["1.1", "MP TRAY", "MP TRAY", "0", "0", "0", "-1"]],
        [
            (0, "MP TRAY"),
            (0, "Status: Available and idle"),
            (False, "Alerts: None"),
        ],
    ),
    (
        "MP TRAY",
        {
            "capacity_levels": (0.0, 0.0),
        },
        [["1.1", "MP TRAY", "MP TRAY", "96", "0", "0", "0"]],
        [
            (0, "MP TRAY"),
            (2, "Offline"),
            (0, "Transitioning"),
            (0, "Status: Available and idle"),
            (False, "Alerts: None"),
            (0, 'Capacity: 0 unknown'),
        ],
    ),
    (
        "MP TRAY",
        {
            "capacity_levels": (0.0, 0.0),
        },
        [["1.1", "MP TRAY", "MP TRAY", "10", "0", "0", "0"]],
        [
            (0, "MP TRAY"),
            (0, "Status: Available and standby"),
            (True, "Alerts: Non-Critical"),
            (0, 'Capacity: 0 unknown'),
        ],
    ),
    (
        "MP TRAY",
        {
            "capacity_levels": (0.0, 0.0),
        },
        [["1.1", "MP TRAY", "MP TRAY", "18", "0", "0", "0"]],
        [
            (0, "MP TRAY"),
            (0, "Status: Available and standby"),
            (2, "Alerts: Critical"),
            (0, 'Capacity: 0 unknown'),
        ],
    ),
    (
        "MP TRAY",
        {
            "capacity_levels": (0.0, 0.0),
        },
        [["1.1", "MP TRAY", "MP TRAY", "0", "8", "-2", "11"]],
        [
            (0, "MP TRAY"),
            (0, "Status: Available and idle"),
            (False, "Alerts: None"),
            (0, 'Capacity: 11 sheets'),
        ],
    ),
    (
        "MP TRAY",
        {
            "capacity_levels": (0.0, 0.0),
        },
        [["1.1", "MP TRAY", "MP TRAY", "0", "", "-2", "11"]],
        [
            (0, "MP TRAY"),
            (0, "Status: Available and idle"),
            (False, "Alerts: None"),
            (0, 'Capacity: 11'),
        ],
    ),
    (
        "MP TRAY",
        {
            "capacity_levels": (0.0, 0.0),
        },
        [["1.1", "MP TRAY", "MP TRAY", "0", "18", "15", "-3"]],
        [
            (0, "MP TRAY"),
            (0, "Status: Available and idle"),
            (False, "Alerts: None"),
            (0, "Maximal capacity: 15 items"),
            (0, "At least one remaining"),
        ],
    ),
    (
        "MP TRAY",
        {
            "capacity_levels": (0.0, 0.0),
        },
        [["1.1", "MP TRAY", "MP TRAY", "0", "8", "15", "11"]],
        [
            (0, "MP TRAY"),
            (0, "Status: Available and idle"),
            (False, "Alerts: None"),
            (0, "Maximal capacity: 15 sheets"),
            (0, 'Remaining: 73.33%', []),
        ],
    ),
    (
        "1",
        {
            "capacity_levels": (80, 20),
        },
        [["1.1", "", "", "0", "8", "15", "11"]],
        [
            (0, ""),
            (0, "Status: Available and idle"),
            (False, "Alerts: None"),
            (0, "Maximal capacity: 15 sheets"),
            (1, 'Remaining: 73.33% (warn/crit below 80.0%/20.0%)', []),
        ],
    ),
    (
        "15",
        {
            "capacity_levels": (80, 20),
        },
        [["1.1", "", "", "0", "8", "15", "11"]],
        [],
    ),
])
def test_check_printer_input(item, params, info, expected_result):
    data = Check("printer_input").run_parse(info)
    result = Check("printer_input").run_check(item, params, data)
    assert list(result) == expected_result


@pytest.mark.parametrize("item, params, info, expected_result", [
    (
        "MP TRAY",
        {
            "capacity_levels": (0.0, 0.0),
        },
        [["1.1", "MP TRAY", "MP TRAY", "0", "18", "15", "-3"]],
        [
            (0, "MP TRAY"),
            (0, "Status: Available and idle"),
            (False, "Alerts: None"),
            (0, "Maximal capacity: 15 items"),
            (0, "At least one filled"),
        ],
    ),
    (
        "1",
        {
            "capacity_levels": (70, 80),
        },
        [["1.1", "", "", "0", "8", "15", "11"]],
        [
            (0, ""),
            (0, "Status: Available and idle"),
            (False, "Alerts: None"),
            (0, "Maximal capacity: 15 sheets"),
            (1, 'Filled: 73.33% (warn/crit at 70.0%/80.0%)', []),
        ],
    ),
])
def test_check_priner_output(item, params, info, expected_result):
    data = Check("printer_output").run_parse(info)
    result = Check("printer_output").run_check(item, params, data)
    assert list(result) == expected_result


@pytest.mark.parametrize("info, expected_result", [([
    ["1.1", "MP TRAY1", "", "0", "8", "15", "11"],
    ["1.1", "MP TRAY2", "MP TRAY", "0", "8", "0", "11"],
    ["1.1", "MP TRAY3", "MP TRAY", "3", "8", "5", "11"],
    ["1.1", "MP TRAY4", "MP TRAY", "6", "8", "6", "11"],
], [("MP TRAY4", {})])])
def test_inventory_printer_io(info, expected_result):
    data = Check("printer_output").run_parse(info)
    result = Check("printer_output").run_discovery(data)
    assert list(result) == expected_result
