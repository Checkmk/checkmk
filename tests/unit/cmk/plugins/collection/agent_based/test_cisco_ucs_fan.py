#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

import pytest

from cmk.agent_based.v2 import CheckResult, Result, Service, State
from cmk.plugins.collection.agent_based.cisco_ucs_fan import (
    check_cisco_ucs_fan,
    discover_cisco_ucs_fan,
    FanModule,
    parse_cisco_ucs_fan,
)
from cmk.plugins.collection.agent_based.cisco_ucs_fault_section import parse_cisco_ucs_fault
from cmk.plugins.lib.cisco_ucs import Fault


@pytest.fixture(name="section_cisco_ucs_fan", scope="module")
def fixture_section_cisco_ucs_fan() -> dict[str, FanModule]:
    return parse_cisco_ucs_fan(
        [
            ["sys/rack-unit-1/fan-module-1-1/fan-1", "1"],
            ["sys/rack-unit-1/fan-module-1-1/fan-2", "1"],
            ["sys/rack-unit-1/fan-module-1-2/fan-1", "1"],
            ["sys/rack-unit-1/fan-module-1-2/fan-2", "1"],
            ["sys/rack-unit-1/fan-module-1-3/fan-1", "1"],
            ["sys/rack-unit-1/fan-module-1-3/fan-2", "1"],
            ["sys/rack-unit-1/fan-module-1-4/fan-1", "1"],
            ["sys/rack-unit-1/fan-module-1-4/fan-2", "1"],
            ["sys/rack-unit-1/fan-module-1-5/fan-1", "1"],
            ["sys/rack-unit-1/fan-module-1-5/fan-2", "1"],
            ["sys/rack-unit-1/fan-module-1-6/fan-1", "1"],
            ["sys/rack-unit-1/fan-module-1-6/fan-2", "1"],
            ["sys/rack-unit-1/fan-module-1-7/fan-1", "1"],
            ["sys/rack-unit-1/fan-module-1-7/fan-2", "1"],
        ]
    )


@pytest.fixture(name="section_cisco_ucs_fault", scope="module")
def fixture_section_ucs_fault() -> dict[str, list[Fault]]:
    return parse_cisco_ucs_fault(
        [
            [
                "sys/rack-unit-1/fan-module-1-7/fan-1",
                "1",
                "185",
                "Some fan fault",
                "5",
            ]
        ]
    )


def test_discover_cisco_ucs_fan(
    section_cisco_ucs_fan: Mapping[str, FanModule],
) -> None:
    assert list(discover_cisco_ucs_fan(section_cisco_ucs_fan, None)) == [
        Service(item="fan-module-1-1 fan-1"),
        Service(item="fan-module-1-1 fan-2"),
        Service(item="fan-module-1-2 fan-1"),
        Service(item="fan-module-1-2 fan-2"),
        Service(item="fan-module-1-3 fan-1"),
        Service(item="fan-module-1-3 fan-2"),
        Service(item="fan-module-1-4 fan-1"),
        Service(item="fan-module-1-4 fan-2"),
        Service(item="fan-module-1-5 fan-1"),
        Service(item="fan-module-1-5 fan-2"),
        Service(item="fan-module-1-6 fan-1"),
        Service(item="fan-module-1-6 fan-2"),
        Service(item="fan-module-1-7 fan-1"),
        Service(item="fan-module-1-7 fan-2"),
    ]


@pytest.mark.parametrize(
    "item, expected_output",
    [
        pytest.param("missing", [], id="Item missing in data"),
        pytest.param(
            "fan-module-1-7 fan-2",
            [
                Result(state=State.OK, summary="Status: operable"),
                Result(state=State.OK, notice="No faults"),
            ],
            id="Last item in data",
        ),
        pytest.param(
            "fan-module-1-7 fan-1",
            [
                Result(state=State.OK, summary="Status: operable"),
                Result(
                    state=State.CRIT,
                    notice="Fault: 185 - Some fan fault",
                ),
            ],
            id="Faulty item in data",
        ),
    ],
)
def test_check_cisco_ucs_mem(
    section_cisco_ucs_fan: Mapping[str, FanModule],
    section_cisco_ucs_fault: Mapping[str, Sequence[Fault]],
    item: str,
    expected_output: CheckResult,
) -> None:
    assert (
        list(check_cisco_ucs_fan(item, section_cisco_ucs_fan, section_cisco_ucs_fault))
        == expected_output
    )
