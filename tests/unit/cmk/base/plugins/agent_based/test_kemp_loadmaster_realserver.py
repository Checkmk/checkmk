#!/usr/bin/env python3
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

import cmk.base.plugins.agent_based.kemp_loadmaster_realserver as klr
from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, Service, State
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import StringTable


@pytest.fixture(name="section")
def section_fixture() -> klr.Section:
    return klr.parse_kemp_loadmaster_realserver(
        [
            ["10.20.30.101", "1"],  # This data is based on SUP-8769
            ["10.20.30.102", "1"],
            ["10.20.30.101", "2"],
            ["10.20.30.102", "2"],
            ["10.20.30.101", "3"],
            ["10.20.30.102", "3"],
        ]
    )


def test_discovery(section: klr.Section) -> None:
    assert list(klr.discover_kemp_loadmaster_realserver(section)) == [
        Service(item="10.20.30.101"),
        Service(item="10.20.30.102"),
    ]


@pytest.mark.parametrize(
    "string_table, expect_discovered_services",
    [
        pytest.param(
            [
                ["10.20.30.101", "4"],
                ["10.20.30.101", "4"],
                ["10.20.30.101", "4"],
            ],
            False,
            id="If all states are disabled, we do not want discovery.",
        ),
        pytest.param(
            [
                ["10.20.30.101", "1"],
                ["10.20.30.101", "1"],
                ["10.20.30.101", "4"],
            ],
            True,
            id="If one state is not disabled, we want discovery.",
        ),
    ],
)
def test_discovery_with_disabled_services(
    string_table: StringTable, expect_discovered_services: bool
) -> None:
    section = klr.parse_kemp_loadmaster_realserver(string_table)
    discovered_services = bool(list(klr.discover_kemp_loadmaster_realserver(section)))
    assert discovered_services == expect_discovered_services


@pytest.mark.parametrize("item", ["10.20.30.101", "10.20.30.102"])
def test_check(item: str, section: klr.Section) -> None:
    assert list(klr.check_kemp_loadmaster_realserver(item, section)) == [
        Result(state=State.OK, summary="In service"),
        Result(state=State.CRIT, summary="Out of service"),
        Result(state=State.CRIT, summary="Failed"),
    ]
