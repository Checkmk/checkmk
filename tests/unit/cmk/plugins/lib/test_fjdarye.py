#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.agent_based.v2 import CheckResult, DiscoveryResult, Result, Service, State, StringTable
from cmk.plugins.lib.fjdarye import (
    check_fjdarye_item,
    discover_fjdarye_item,
    FjdaryeItem,
    parse_fjdarye_item,
    SectionFjdaryeItem,
)


@pytest.mark.parametrize(
    # Assumption: Section will always be a List[StringTable]
    # The string_table consists of 3 lists of lists.
    # The first list has data about the first item of [fjdarye100, fjdarye101, fjdarye500] and so on for the other ones.
    "string_table, parse_result",
    [
        pytest.param(
            [
                [
                    ["0", "1"],
                    ["1", "1"],
                    ["2", "1"],
                    ["3", "1"],
                    ["4", "4"],
                ],
                [],
                [],
            ],
            {
                "0": FjdaryeItem(item_index="0", status="1"),
                "1": FjdaryeItem(item_index="1", status="1"),
                "2": FjdaryeItem(item_index="2", status="1"),
                "3": FjdaryeItem(item_index="3", status="1"),
                "4": FjdaryeItem(item_index="4", status="4"),
            },
            id="Parse the string_table into a Mapping[str, FjdaryeItem]",
        ),
        pytest.param(
            [],
            {},
            id="If the string_table is empty, no items are parsed",
        ),
    ],
)
def test_parse_fjdarye_item(
    string_table: list[StringTable],
    parse_result: SectionFjdaryeItem,
) -> None:
    assert parse_fjdarye_item(string_table) == parse_result


@pytest.mark.parametrize(
    "section, discovery_result",
    [
        pytest.param(
            {
                "0": FjdaryeItem(item_index="0", status="1"),
                "1": FjdaryeItem(item_index="1", status="1"),
                "2": FjdaryeItem(item_index="2", status="1"),
                "3": FjdaryeItem(item_index="3", status="1"),
            },
            [
                Service(item="0"),
                Service(item="1"),
                Service(item="2"),
                Service(item="3"),
            ],
            id="Four valid items are discovered from the section",
        ),
        pytest.param(
            {
                "4": FjdaryeItem(item_index="4", status="4"),
            },
            [],
            id="Discovery ignores items that have a status of 4 (invalid) and because of that no items are discovered",
        ),
        pytest.param(
            {},
            [],
            id="If the section is empty, no items are discovered",
        ),
    ],
)
def test_discover_fjdarye_item(
    section: SectionFjdaryeItem,
    discovery_result: DiscoveryResult,
) -> None:
    assert list(discover_fjdarye_item(section)) == discovery_result


@pytest.mark.parametrize(
    # Assumption: The fjdarye_disks_status mapping consistantly gives us a tuple of (state, state_description)
    "section, item, check_result",
    [
        pytest.param(
            {
                "0": FjdaryeItem(item_index="0", status="1"),
                "1": FjdaryeItem(item_index="1", status="1"),
                "2": FjdaryeItem(item_index="2", status="1"),
                "3": FjdaryeItem(item_index="3", status="1"),
            },
            "1",
            [Result(state=State.OK, summary="Normal")],
            id="If the given item is present in the section, the check result state and check summary are the mapped tuple from fjdarye_item_status",
        ),
        pytest.param(
            {},
            "4",
            [],
            id="If the raw section is empty, the check result is None",
        ),
        pytest.param(
            {
                "0": FjdaryeItem(item_index="0", status="1"),
                "1": FjdaryeItem(item_index="1", status="1"),
                "2": FjdaryeItem(item_index="2", status="1"),
                "3": FjdaryeItem(item_index="3", status="1"),
            },
            "13",
            [],
            id="If the given item is not present in the raw section, the check result is None",
        ),
    ],
)
def test_check_fjdarye_item(
    section: SectionFjdaryeItem,
    item: str,
    check_result: CheckResult,
) -> None:
    assert list(check_fjdarye_item(item, section)) == check_result
