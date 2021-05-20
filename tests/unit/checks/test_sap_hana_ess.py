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
            ["[[HXE 90 HXE]]"],
            ["started", "0"],
            ["active", "no"],
        ],
        {
            "HXE 90 HXE": {
                "active": "no",
                "started": 0
            }
        },
    ),
    (
        [
            ["[[HXE 90 HXE]]"],
            ["started"],
            ["active", "no"],
        ],
        {
            "HXE 90 HXE": {
                "active": "no"
            }
        },
    ),
    (
        [
            ["[[HXE 90 HXE]]"],
            ["started", "a"],
            ["active", "no"],
        ],
        {
            "HXE 90 HXE": {
                "active": "no"
            }
        },
    ),
])
def test_parse_sap_hana_ess(info, expected_result):
    result = Check("sap_hana_ess").run_parse(info)
    assert result == expected_result


@pytest.mark.parametrize("info, expected_result", [
    (
        [
            ["[[HXE 90 HXE]]"],
            ["started", "0"],
            ["active", "no"],
        ],
        [("HXE 90 HXE", {})],
    ),
])
def test_inventory_sap_hana_ess(info, expected_result):
    section = Check("sap_hana_ess").run_parse(info)
    result = Check("sap_hana_ess").run_discovery(section)
    assert list(result) == expected_result


@pytest.mark.parametrize("item, info, expected_result", [
    (
        "HXE 90 HXE",
        [
            ["[[HXE 90 HXE]]"],
            ["started", "0"],
            ["active", "no"],
        ],
        [
            (2, "Active status: no"),
            (2, "Started threads: 0", [("threads", 0)]),
        ],
    ),
    (
        "HXE 90 HXE",
        [
            ["[[HXE 90 HXE]]"],
            ["started", "1"],
            ["active", "yes"],
        ],
        [
            (0, "Active status: yes"),
            (0, "Started threads: 1", [("threads", 1)]),
        ],
    ),
    (
        "HXE 90 HXE",
        [
            ["[[HXE 90 HXE]]"],
            ["started", "1"],
            ["active", "unknown"],
        ],
        [
            (3, "Active status: unknown"),
            (0, "Started threads: 1", [("threads", 1)]),
        ],
    ),
])
def test_check_sap_hana_ess(item, info, expected_result):
    section = Check("sap_hana_ess").run_parse(info)
    result = Check("sap_hana_ess").run_check(item, {}, section)
    assert list(result) == expected_result