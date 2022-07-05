#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from tests.testlib import Check

STRING_TABLE = [
    ["vs adaptive method type", "1", "100"],
    ["another vs adaptive method type", "1", "200"],
    ["yet another vs adaptive method type", "4", "100"],
    ["Bar", "8", "0"],
]


@pytest.fixture(name="section")
def section_fixture():
    check = Check("kemp_loadmaster_services")
    return check.run_parse(info=STRING_TABLE)


@pytest.mark.parametrize(
    "expected_services",
    [
        [
            ("vs adaptive method type", "kemp_loadmaster_service_default_levels"),
            ("another vs adaptive method type", "kemp_loadmaster_service_default_levels"),
            ("Bar", "kemp_loadmaster_service_default_levels"),
        ],
    ],
)
def test_discovery_kemp_loadmaster_services(section, expected_services) -> None:
    check = Check("kemp_loadmaster_services")
    assert list(check.run_discovery(section)) == expected_services


@pytest.mark.parametrize(
    "item, expected_results",
    [
        (
            "another vs adaptive method type",
            [
                (0, "Status: in service"),
                (0, "Active connections: 200", [("conns", 200)]),
            ],
        ),
        (
            "vs adaptive method type",
            [
                (0, "Status: in service"),
                (0, "Active connections: 100", [("conns", 100)]),
            ],
        ),
        (
            "Bar",
            [
                (3, "Status: unknown[8]"),
                (0, "Active connections: 0", [("conns", 0)]),
            ],
        ),
    ],
)
def test_check_kemp_loadmaster_services(section, item: str, expected_results) -> None:
    check = Check("kemp_loadmaster_services")
    assert list(check.run_check(item=item, params=(1500, 2000), info=section)) == expected_results
