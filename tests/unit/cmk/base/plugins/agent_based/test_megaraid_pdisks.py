#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Final

import pytest

from cmk.base.plugins.agent_based import megaraid_pdisks
from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, Service, State
from cmk.base.plugins.agent_based.utils import megaraid

STRING_TABLE: Final = [
    ["Enclosure", "Device", "ID:", "10"],
    ["Slot", "Number:", "0"],
    ["Device", "Id:", "4"],
    ["Raw", "Size:", "140014MB", "[0x11177330", "Sectors]"],
    ["Firmware", "state:", "Unconfigured(good)"],
    ["Predictive", "Failure", "Count:", "10"],
    ["Inquiry", "Data:", "FUJITSU", "MBB2147RC", "5204BS04P9104BV5"],
    ["Enclosure", "Device", "ID:", "11"],
    ["Slot", "Number:", "1"],
    ["Device", "Id:", "5"],
    ["Raw", "Size:", "140014MB", "[0x11177330", "Sectors]"],
    ["Firmware", "state:", "Unconfigured(good)"],
    ["Inquiry", "Data:", "FUJITSU", "MBB2147RC", "5204BS04P9104BSC"],
    ["Enclosure", "Device", "ID:", "12"],
    ["Slot", "Number:", "2"],
    ["Device", "Id:", "6"],
    ["Raw", "Size:", "140014MB", "[0x11177330", "Sectors]"],
    ["Predictive", "Failure", "Count:", "19"],
    ["Firmware", "state:", "Failed"],
    ["Inquiry", "Data:", "FUJITSU", "MBB2147RC", "5204BS04P9104BSC"],
]


@pytest.fixture(name="section", scope="module")
def _get_section() -> megaraid.SectionPDisks:
    return megaraid_pdisks.parse_megaraid_pdisks(STRING_TABLE)


def test_discovery(section: megaraid.SectionPDisks) -> None:
    assert list(megaraid_pdisks.discover_megaraid_pdisks(section)) == [
        Service(item="/c0/e10/s0"),
        Service(item="/c0/e11/s1"),
        Service(item="/c0/e12/s2"),
    ]


def test_check_unconf_good(section: megaraid.SectionPDisks) -> None:
    assert list(
        megaraid_pdisks.check_megaraid_pdisks("/c0/e10/s0", {"Unconfigured Good": 0}, section)
    ) == [
        Result(state=State.OK, summary="Unconfigured good"),
        Result(state=State.OK, summary="Name: FUJITSU MBB2147RC 5204BS04P9104BV5"),
        Result(state=State.WARN, summary="Predictive fail count: 10"),
    ]


def test_check_failed(section: megaraid.SectionPDisks) -> None:
    assert list(megaraid_pdisks.check_megaraid_pdisks("e12/2", {"Failed": 2}, section)) == [
        Result(state=State.CRIT, summary="Failed"),
        Result(
            state=State.OK,
            summary="Name: FUJITSU MBB2147RC 5204BS04P9104BSC",
        ),
        Result(
            state=State.WARN,
            summary="Predictive fail count: 19",
        ),
    ]
