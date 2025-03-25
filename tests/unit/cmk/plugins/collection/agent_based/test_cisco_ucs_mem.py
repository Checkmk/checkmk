#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

import pytest

from cmk.agent_based.v2 import CheckResult, Result, Service, State
from cmk.plugins.collection.agent_based.cisco_ucs_fault_section import parse_cisco_ucs_fault
from cmk.plugins.collection.agent_based.cisco_ucs_mem import (
    check_cisco_ucs_mem,
    discover_cisco_ucs_mem,
    MemoryModule,
    parse_cisco_ucs_mem,
)
from cmk.plugins.lib.cisco_ucs import Fault


@pytest.fixture(name="section_cisco_ucs_mem", scope="module")
def fixture_section_ucs_mem() -> dict[str, MemoryModule]:
    return parse_cisco_ucs_mem(
        [
            [
                "mem-1",
                "0357CDB9",
                "26",
                "32768",
                "1",
                "10",
                "sys/rack-unit-1/board/memarray-1/mem-1",
            ],
            [
                "mem-2",
                "0357CF3B",
                "26",
                "32768",
                "1",
                "10",
                "sys/rack-unit-1/board/memarray-1/mem-2",
            ],
            [
                "mem-3",
                "418686A5",
                "26",
                "32768",
                "1",
                "10",
                "sys/rack-unit-1/board/memarray-1/mem-3",
            ],
            [
                "mem-4",
                "41867F58",
                "26",
                "32768",
                "1",
                "10",
                "sys/rack-unit-1/board/memarray-1/mem-4",
            ],
            [
                "mem-5",
                "41869BEB",
                "26",
                "32768",
                "1",
                "10",
                "sys/rack-unit-1/board/memarray-1/mem-5",
            ],
            ["mem-6", "NA", "0", "0", "0", "11", "sys/rack-unit-1/board/memarray-1/mem-6"],
            [
                "mem-7",
                "0357CE24",
                "26",
                "32768",
                "1",
                "10",
                "sys/rack-unit-1/board/memarray-1/mem-7",
            ],
            [
                "mem-8",
                "0357CCDF",
                "26",
                "32768",
                "1",
                "10",
                "sys/rack-unit-1/board/memarray-1/mem-8",
            ],
            [
                "mem-9",
                "0357CD64",
                "26",
                "32768",
                "1",
                "10",
                "sys/rack-unit-1/board/memarray-1/mem-9",
            ],
            [
                "mem-10",
                "0357CE2E",
                "26",
                "32768",
                "1",
                "10",
                "sys/rack-unit-1/board/memarray-1/mem-10",
            ],
            [
                "mem-11",
                "418D4B03",
                "26",
                "32768",
                "1",
                "10",
                "sys/rack-unit-1/board/memarray-1/mem-11",
            ],
            ["mem-12", "NA", "0", "0", "0", "11", "sys/rack-unit-1/board/memarray-1/mem-12"],
            ["mem-13", "NA", "0", "0", "0", "11", "sys/rack-unit-1/board/memarray-1/mem-13"],
            ["mem-14", "NA", "0", "0", "0", "11", "sys/rack-unit-1/board/memarray-1/mem-14"],
            [
                "mem-15",
                "0357CDF9",
                "26",
                "32768",
                "1",
                "10",
                "sys/rack-unit-1/board/memarray-1/mem-15",
            ],
            [
                "mem-16",
                "0357CE15",
                "26",
                "32768",
                "1",
                "10",
                "sys/rack-unit-1/board/memarray-1/mem-16",
            ],
            [
                "mem-17",
                "41867C12",
                "26",
                "32768",
                "1",
                "10",
                "sys/rack-unit-1/board/memarray-1/mem-17",
            ],
            ["mem-18", "NA", "0", "0", "0", "11", "sys/rack-unit-1/board/memarray-1/mem-18"],
            [
                "mem-19",
                "03584CA9",
                "26",
                "32768",
                "1",
                "10",
                "sys/rack-unit-1/board/memarray-1/mem-19",
            ],
            [
                "mem-20",
                "418CCC3E",
                "26",
                "32768",
                "1",
                "10",
                "sys/rack-unit-1/board/memarray-1/mem-20",
            ],
            [
                "mem-21",
                "418686E5",
                "26",
                "32768",
                "1",
                "10",
                "sys/rack-unit-1/board/memarray-1/mem-21",
            ],
            [
                "mem-22",
                "419B0A7A",
                "26",
                "32768",
                "1",
                "10",
                "sys/rack-unit-1/board/memarray-1/mem-22",
            ],
            [
                "mem-23",
                "41868484",
                "26",
                "32768",
                "1",
                "10",
                "sys/rack-unit-1/board/memarray-1/mem-23",
            ],
            ["mem-24", "NA", "0", "0", "0", "11", "sys/rack-unit-1/board/memarray-1/mem-24"],
        ]
    )


@pytest.fixture(name="section_cisco_ucs_fault", scope="module")
def fixture_section_ucs_fault() -> dict[str, list[Fault]]:
    return parse_cisco_ucs_fault(
        [
            [
                "sys/rack-unit-1/board/memarray-1/mem-15",
                "1",
                "185",
                "DDR4_P2_G2_ECC: DIMM 14 is inoperable : Check or replace DIMM",
                "5",
            ]
        ]
    )


def test_discover_cisco_ucs_mem(section_cisco_ucs_mem: Mapping[str, MemoryModule]) -> None:
    assert list(discover_cisco_ucs_mem(section_cisco_ucs_mem, None)) == [
        Service(item="mem-1"),
        Service(item="mem-2"),
        Service(item="mem-3"),
        Service(item="mem-4"),
        Service(item="mem-5"),
        Service(item="mem-7"),
        Service(item="mem-8"),
        Service(item="mem-9"),
        Service(item="mem-10"),
        Service(item="mem-11"),
        Service(item="mem-15"),
        Service(item="mem-16"),
        Service(item="mem-17"),
        Service(item="mem-19"),
        Service(item="mem-20"),
        Service(item="mem-21"),
        Service(item="mem-22"),
        Service(item="mem-23"),
    ]


@pytest.mark.parametrize(
    "item, expected_output",
    [
        pytest.param("missing", [], id="Item missing in data"),
        pytest.param(
            "mem-1",
            [
                Result(state=State.OK, summary="Status: operable"),
                Result(state=State.OK, summary="Presence: equipped"),
                Result(state=State.OK, summary="Type: ddr4"),
                Result(state=State.OK, summary="Size: 32768 MB, SN: 0357CDB9"),
                Result(state=State.OK, notice="No faults"),
            ],
            id="Item in data no fault",
        ),
        pytest.param(
            "mem-15",
            [
                Result(state=State.OK, summary="Status: operable"),
                Result(state=State.OK, summary="Presence: equipped"),
                Result(state=State.OK, summary="Type: ddr4"),
                Result(state=State.OK, summary="Size: 32768 MB, SN: 0357CDF9"),
                Result(
                    state=State.CRIT,
                    notice="Fault: 185 - DDR4_P2_G2_ECC: DIMM 14 is inoperable : Check or replace DIMM",
                ),
            ],
            id="Item in data with fault",
        ),
    ],
)
def test_check_cisco_ucs_mem(
    section_cisco_ucs_mem: Mapping[str, MemoryModule],
    section_cisco_ucs_fault: Mapping[str, Sequence[Fault]],
    item: str,
    expected_output: CheckResult,
) -> None:
    assert (
        list(check_cisco_ucs_mem(item, section_cisco_ucs_mem, section_cisco_ucs_fault))
        == expected_output
    )
