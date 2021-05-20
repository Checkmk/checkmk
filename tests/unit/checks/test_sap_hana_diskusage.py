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
            ["Data", "OK", "Size 64.3 GB, Used 10.1 GB, Free 85 %"],
            ["Log", "OK", "Size 64.3 GB, Used 10.1 GB, Free 85 %"],
            ["Trace", "OK", "Size 64.3 GB, Used 10.1 GB, Free 85 %"],
        ],
        {
            "HXE 90 HXE - Data": {
                "size": 65843.2,
                "state_name": "OK",
                "used": 10342.4
            },
            "HXE 90 HXE - Log": {
                "size": 65843.2,
                "state_name": "OK",
                "used": 10342.4
            },
            "HXE 90 HXE - Trace": {
                "size": 65843.2,
                "state_name": "OK",
                "used": 10342.4
            }
        },
    ),
    (
        [
            ["[[HXE 90 HXE]]"],
            ["Data", "OK", "Size 64.3a GB, Used 10.1 GB, Free 85 %"],
            ["Log", "OK"],
            ["Trace", "OK", "Size 64.3 GB, Used 10.1 GB, Free 85 %"],
        ],
        {
            "HXE 90 HXE - Data": {
                "state_name": "OK",
                "used": 10342.4
            },
            "HXE 90 HXE - Trace": {
                "size": 65843.2,
                "state_name": "OK",
                "used": 10342.4
            }
        },
    ),
])
def test_parse_sap_hana_diskusage(info, expected_result):
    result = Check("sap_hana_diskusage").run_parse(info)
    assert result == expected_result


@pytest.mark.parametrize("info, expected_result", [
    ([
        ["[[HXE 90 HXE]]"],
        ["Data", "OK", "Size 64.3 GB, Used 10.1 GB, Free 85 %"],
        ["Log", "OK", "Size 64.3 GB, Used 10.1 GB, Free 85 %"],
        ["Trace", "OK", "Size 64.3 GB, Used 10.1 GB, Free 85 %"],
    ], [
        ("HXE 90 HXE - Data", {}),
        ("HXE 90 HXE - Log", {}),
        ("HXE 90 HXE - Trace", {}),
    ]),
])
def test_inventory_sap_hana_diskusage(info, expected_result):
    section = Check("sap_hana_diskusage").run_parse(info)
    result = Check("sap_hana_diskusage").run_discovery(section)
    assert list(result) == expected_result


@pytest.mark.parametrize("item, info, expected_result", [
    (
        "HXE 90 HXE - Data",
        [
            ["[[HXE 90 HXE]]"],
            ["Data", "OK", "Size 64.3 GB, Used 10.1 GB, Free 85 %"],
            ["Log", "OK", "Size 64.3 GB, Used 10.1 GB, Free 85 %"],
            ["Trace", "OK", "Size 64.3 GB, Used 10.1 GB, Free 85 %"],
        ],
        [
            (0, "Status: OK"),
            (0, "15.71% used (10.10 of 64.30 GB)", [
                ("fs_used", 10342.400000000001, 52674.56, 59258.88, 0, 65843.2),
                ("fs_size", 65843.2), ("fs_used_percent", 15.707620528771386)
            ]),
        ],
    ),
    (
        "HXE 90 HXE - Log",
        [
            ["[[HXE 90 HXE]]"],
            ["Log", "UNKNOWN", "Size 64.3 GB, Used 10.1 GB, Free 85 %"],
        ],
        [
            (3, "Status: UNKNOWN"),
            (0, "15.71% used (10.10 of 64.30 GB)", [
                ("fs_used", 10342.400000000001, 52674.56, 59258.88, 0, 65843.2),
                ("fs_size", 65843.2), ("fs_used_percent", 15.707620528771386)
            ]),
        ],
    ),
    (
        "HXE 90 HXE - Log",
        [
            ["[[HXE 90 HXE]]"],
            ["Log", "STATE", "Size 64.3 GB, Used 10.1 GB, Free 85 %"],
        ],
        [
            (2, "Status: STATE"),
            (0, "15.71% used (10.10 of 64.30 GB)", [
                ("fs_used", 10342.400000000001, 52674.56, 59258.88, 0, 65843.2),
                ("fs_size", 65843.2), ("fs_used_percent", 15.707620528771386)
            ]),
        ],
    ),
])
def test_check_sap_hana_diskusage(item, info, expected_result):
    section = Check("sap_hana_diskusage").run_parse(info)
    result = Check("sap_hana_diskusage").run_check(item, {}, section)
    assert list(result) == expected_result