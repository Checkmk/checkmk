#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from testlib import Check


@pytest.mark.parametrize("info, expected_result", [
    ([
        ["[[HXE 90 SYSTEMDB]]"],
        ["open_events", "4"],
        ["disabled_alerts", "1"],
        ["high_alerts", "0"],
    ], {
        "HXE 90 SYSTEMDB": {
            "disabled_alerts": 1,
            "high_alerts": 0,
            "open_events": 4
        },
    }),
    ([
        ["[[HXE 90 SYSTEMDB]]"],
        ["open_events", "a"],
        ["disabled_alerts"],
        ["high_alerts", "0"],
    ], {
        "HXE 90 SYSTEMDB": {
            "high_alerts": 0,
        },
    }),
])
def test_parse_sap_hana_events(info, expected_result):
    result = Check("sap_hana_events").run_parse(info)
    assert result == expected_result


@pytest.mark.parametrize("info, expected_result", [
    (
        [
            ["[[HXE 90 SYSTEMDB]]"],
            ["open_events", "4"],
            ["disabled_alerts", "1"],
            ["high_alerts", "0"],
        ],
        [("HXE 90 SYSTEMDB", {})],
    ),
])
def test_inventory_sap_hana_events(info, expected_result):
    section = Check("sap_hana_events").run_parse(info)
    result = Check("sap_hana_events").run_discovery(section)
    assert list(result) == expected_result


@pytest.mark.parametrize("item, info, expected_result", [
    (
        "HXE 90 SYSTEMDB",
        [
            ["[[HXE 90 SYSTEMDB]]"],
            ["open_events", "4"],
            ["disabled_alerts", "1"],
            ["high_alerts", "0"],
        ],
        [
            (2, "Unacknowledged events: 4", [("num_open_events", 4)]),
            (1, "Disabled alerts: 1", [("num_disabled_alerts", 1)]),
            (0, "High alerts: 0", [("num_high_alerts", 0)]),
        ],
    ),
])
def test_check_sap_hana_events(item, info, expected_result):
    section = Check("sap_hana_events").run_parse(info)
    result = Check("sap_hana_events").run_check(item, {}, section)
    assert list(result) == expected_result