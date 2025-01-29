#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

import pytest

from cmk.agent_based.v2 import Metric, Result, Service, State
from cmk.plugins.collection.agent_based.kemp_loadmaster_services import (
    check_kemp_loadmaster_services,
    discover_kemp_loadmaster_services,
    parse_kemp_loadmaster_services,
)
from cmk.plugins.lib.kemp_loadmaster import VSSection

STRING_TABLE = [
    ["vs adaptive method type", "1", "100", "1"],
    ["another vs adaptive method type", "1", "200", "2"],
    ["yet another vs adaptive method type", "4", "100", "3"],
    ["Bar", "8", "0", "4"],
]


@pytest.fixture(name="section")
def section_fixture():
    return parse_kemp_loadmaster_services(STRING_TABLE)


@pytest.mark.parametrize(
    "expected_services",
    [
        [
            Service(item="vs adaptive method type"),
            Service(item="another vs adaptive method type"),
            Service(item="Bar"),
        ],
    ],
)
def test_discovery_kemp_loadmaster_services(
    section: VSSection, expected_services: Sequence[Service]
) -> None:
    assert list(discover_kemp_loadmaster_services(section)) == expected_services


@pytest.mark.parametrize(
    "item, expected_results",
    [
        (
            "another vs adaptive method type",
            [
                Result(state=State.OK, summary="Status: in service"),
                Result(state=State.OK, summary="Active connections: 200"),
                Metric("conns", 200),
            ],
        ),
        (
            "vs adaptive method type",
            [
                Result(state=State.OK, summary="Status: in service"),
                Result(state=State.OK, summary="Active connections: 100"),
                Metric("conns", 100),
            ],
        ),
        (
            "Bar",
            [
                Result(state=State.UNKNOWN, summary="Status: unknown[8]"),
                Result(state=State.OK, summary="Active connections: 0"),
                Metric("conns", 0),
            ],
        ),
    ],
)
def test_check_kemp_loadmaster_services(
    section: VSSection, item: str, expected_results: Sequence[Result]
) -> None:
    assert list(check_kemp_loadmaster_services(item=item, section=section)) == expected_results
