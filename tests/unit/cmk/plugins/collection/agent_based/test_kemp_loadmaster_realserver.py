#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import pytest

import cmk.plugins.collection.agent_based.kemp_loadmaster_realserver as klr
import cmk.plugins.collection.agent_based.kemp_loadmaster_services as kls
from cmk.agent_based.v2 import Result, Service, State, StringTable
from cmk.plugins.lib.kemp_loadmaster import VSSection


@pytest.fixture(name="rs_section")
def rs_section_fixture() -> klr.RSSection:
    return klr.parse_kemp_loadmaster_realserver(
        [
            ["1", "10.20.30.101", "1"],  # This data is based on SUP-8769
            ["1", "10.20.30.102", "1"],
            ["2", "10.20.30.101", "2"],
            ["2", "10.20.30.102", "2"],
            ["3", "10.20.30.101", "3"],
            ["3", "10.20.30.102", "3"],
        ]
    )


@pytest.fixture(name="vs_section")
def vs_section_fixture() -> VSSection:
    return kls.parse_kemp_loadmaster_services(
        [
            ["name 1", "1", "0", "1"],
            ["name 2", "1", "0", "2"],
            ["name 3", "1", "0", "3"],
        ]
    )


def test_discovery(rs_section: klr.RSSection, vs_section: VSSection) -> None:
    assert list(klr.discover_kemp_loadmaster_realserver(rs_section, vs_section)) == [
        Service(item="10.20.30.101"),
        Service(item="10.20.30.102"),
    ]


@pytest.mark.parametrize(
    "string_table, expect_discovered_services",
    [
        pytest.param(
            [
                ["1", "10.20.30.101", "4"],
                ["2", "10.20.30.101", "4"],
                ["3", "10.20.30.101", "4"],
            ],
            False,
            id="If all states are disabled, we do not want discovery.",
        ),
        pytest.param(
            [
                ["1", "10.20.30.101", "1"],
                ["2", "10.20.30.101", "1"],
                ["3", "10.20.30.101", "4"],
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
    discovered_services = bool(list(klr.discover_kemp_loadmaster_realserver(section, None)))
    assert discovered_services == expect_discovered_services


@pytest.mark.parametrize("item", ["10.20.30.101", "10.20.30.102"])
def test_check(item: str, rs_section: klr.RSSection, vs_section: VSSection) -> None:
    assert list(klr.check_kemp_loadmaster_realserver(item, rs_section, vs_section)) == [
        Result(state=State.OK, summary="name 1: In service"),
        Result(state=State.CRIT, summary="name 2: Out of service"),
        Result(state=State.CRIT, summary="name 3: Failed"),
    ]
