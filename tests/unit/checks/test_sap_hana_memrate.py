#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from testlib import Check


@pytest.mark.parametrize("info, expected_result", [
    (
        [
            ["[[HXE 90 SYSTEMDB]]"],
            ["mem_rate", "5115896693", "7297159168"],
        ],
        {
            "HXE 90 SYSTEMDB": {
                "total": 7297159168,
                "used": 5115896693
            }
        },
    ),
    (
        [
            ["[[HXE 90 SYSTEMDB]]"],
            ["5115896693", "7297159168", "mem_rate"],
        ],
        {},
    ),
    ([
        ["[[HXE 90 SYSTEMDB]]"],
        ["mem_rate", "5115896693a", "7297159168"],
    ], {
        "HXE 90 SYSTEMDB": {
            "total": 7297159168
        }
    }),
])
def test_parse_sap_hana_memrate(info, expected_result):
    result = Check("sap_hana_memrate").run_parse(info)
    assert result == expected_result


@pytest.mark.parametrize("info, expected_result", [
    ([
        ["[[HXE 90 SYSTEMDB]]"],
        ["mem_rate", "5115896693", "7297159168"],
    ], [("HXE 90 SYSTEMDB", {})]),
])
def test_inventory_sap_hana_memrate(info, expected_result):
    section = Check("sap_hana_memrate").run_parse(info)
    result = Check("sap_hana_memrate").run_discovery(section)
    assert list(result) == expected_result


@pytest.mark.parametrize("item, info, expected_result", [
    (
        "HXE 90 SYSTEMDB",
        [
            ["[[HXE 90 SYSTEMDB]]"],
            ["mem_rate", "5115896693", "7297159168"],
        ],
        [(0, "Usage: 70.11% - 4.76 GB of 6.80 GB", [
            ("memory_used", 5115896693, None, None, 0, 7297159168)
        ])],
    ),
])
def test_check_sap_hana_memrate(item, info, expected_result):
    section = Check("sap_hana_memrate").run_parse(info)
    result = Check("sap_hana_memrate").run_check(item, {}, section)
    assert list(result) == expected_result
