#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

import pytest

from cmk.base.legacy_checks.cisco_ucs_mem import check_cisco_ucs_mem, inventory_cisco_ucs_mem
from cmk.base.plugins.agent_based.cisco_ucs_mem import MemoryModule, parse_cisco_ucs_mem


@pytest.fixture(name="section", scope="module")
def fixture_section() -> dict[str, MemoryModule]:
    return parse_cisco_ucs_mem(
        [
            ["mem-1", "0357CDB9", "26", "32768", "1", "10"],
            ["mem-2", "0357CF3B", "26", "32768", "1", "10"],
            ["mem-3", "418686A5", "26", "32768", "1", "10"],
            ["mem-4", "41867F58", "26", "32768", "1", "10"],
            ["mem-5", "41869BEB", "26", "32768", "1", "10"],
            ["mem-6", "NA", "0", "0", "0", "11"],
            ["mem-7", "0357CE24", "26", "32768", "1", "10"],
            ["mem-8", "0357CCDF", "26", "32768", "1", "10"],
            ["mem-9", "0357CD64", "26", "32768", "1", "10"],
            ["mem-10", "0357CE2E", "26", "32768", "1", "10"],
            ["mem-11", "418D4B03", "26", "32768", "1", "10"],
            ["mem-12", "NA", "0", "0", "0", "11"],
            ["mem-13", "NA", "0", "0", "0", "11"],
            ["mem-14", "NA", "0", "0", "0", "11"],
            ["mem-15", "0357CDF9", "26", "32768", "1", "10"],
            ["mem-16", "0357CE15", "26", "32768", "1", "10"],
            ["mem-17", "41867C12", "26", "32768", "1", "10"],
            ["mem-18", "NA", "0", "0", "0", "11"],
            ["mem-19", "03584CA9", "26", "32768", "1", "10"],
            ["mem-20", "418CCC3E", "26", "32768", "1", "10"],
            ["mem-21", "418686E5", "26", "32768", "1", "10"],
            ["mem-22", "419B0A7A", "26", "32768", "1", "10"],
            ["mem-23", "41868484", "26", "32768", "1", "10"],
            ["mem-24", "NA", "0", "0", "0", "11"],
        ]
    )


def test_inventory_cisco_ucs_mem(section: Mapping[str, MemoryModule]) -> None:
    assert list(inventory_cisco_ucs_mem(section)) == [
        ("mem-1", None),
        ("mem-2", None),
        ("mem-3", None),
        ("mem-4", None),
        ("mem-5", None),
        ("mem-7", None),
        ("mem-8", None),
        ("mem-9", None),
        ("mem-10", None),
        ("mem-11", None),
        ("mem-15", None),
        ("mem-16", None),
        ("mem-17", None),
        ("mem-19", None),
        ("mem-20", None),
        ("mem-21", None),
        ("mem-22", None),
        ("mem-23", None),
    ]


@pytest.mark.parametrize(
    "item, expected_output",
    [
        pytest.param("missing", [], id="Item missing in data"),
        pytest.param(
            "mem-1",
            [
                (0, "Status: operable"),
                (0, "Presence: equipped"),
                (0, "Type: ddr4"),
                (0, "Size: 32768 MB, SN: 0357CDB9"),
            ],
            id="Item in data",
        ),
    ],
)
def test_check_cisco_ucs_mem(
    section: Mapping[str, MemoryModule], item: str, expected_output: Sequence[object]
) -> None:
    assert list(check_cisco_ucs_mem(item, None, section)) == expected_output
