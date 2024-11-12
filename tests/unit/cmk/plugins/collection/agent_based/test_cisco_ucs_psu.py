#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

import pytest

from cmk.agent_based.v2 import CheckResult, Result, Service, State
from cmk.plugins.collection.agent_based.cisco_ucs_fault_section import parse_cisco_ucs_fault
from cmk.plugins.collection.agent_based.cisco_ucs_psu import (
    check_cisco_ucs_psu,
    discover_cisco_ucs_psu,
    parse_cisco_ucs_psu,
    PSUModule,
)
from cmk.plugins.lib.cisco_ucs import Fault


@pytest.fixture(name="section_cisco_ucs_psu", scope="module")
def fixture_section_cisco_ucs_psu() -> dict[str, PSUModule]:
    return parse_cisco_ucs_psu(
        [
            ["sys/rack-unit-1/psu-1", "1", "ART2323FCB4", "700-014160-0000"],
            ["sys/rack-unit-1/psu-2", "3", "ART2322F7NZ", "700-014160-0000"],
        ]
    )


@pytest.fixture(name="section_cisco_ucs_fault", scope="module")
def fixture_section_ucs_fault() -> dict[str, list[Fault]]:
    return parse_cisco_ucs_fault(
        [
            [
                "sys/rack-unit-1/psu-2",
                "1",
                "374",
                "PSU2_STATUS: Power Supply 2 has lost input or input is out of range : Check input to PS or replace PS 2",
                "5",
            ]
        ]
    )


def test_discover_cisco_ucs_psu(
    section_cisco_ucs_psu: Mapping[str, PSUModule],
) -> None:
    assert list(discover_cisco_ucs_psu(section_cisco_ucs_psu, None)) == [
        Service(item="psu-1"),
        Service(item="psu-2"),
    ]


@pytest.mark.parametrize(
    "item, expected_output",
    [
        pytest.param("missing", [], id="Item missing in data"),
        pytest.param(
            "psu-1",
            [
                Result(
                    state=State.OK,
                    summary="Status: operable, Model: 700-014160-0000, SN: ART2323FCB4",
                ),
                Result(state=State.OK, notice="No faults"),
            ],
            id="Last item in data",
        ),
        pytest.param(
            "psu-2",
            [
                Result(
                    state=State.CRIT,
                    summary="Status: degraded, Model: 700-014160-0000, SN: ART2322F7NZ",
                ),
                Result(
                    state=State.CRIT,
                    notice="Fault: 374 - PSU2_STATUS: Power Supply 2 has lost input or input is out of range : Check input to PS or replace PS 2",
                ),
            ],
            id="Faulty item in data",
        ),
    ],
)
def test_check_cisco_ucs_mem(
    section_cisco_ucs_psu: Mapping[str, PSUModule],
    section_cisco_ucs_fault: Mapping[str, Sequence[Fault]],
    item: str,
    expected_output: CheckResult,
) -> None:
    assert (
        list(check_cisco_ucs_psu(item, section_cisco_ucs_psu, section_cisco_ucs_fault))
        == expected_output
    )
