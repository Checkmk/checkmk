#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Mapping, Optional, Sequence, Union

import pytest

from cmk.base.check_legacy_includes.fjdarye import (
    check_fjdarye_disks,
    check_fjdarye_disks_summary,
    check_fjdarye_item,
    check_fjdarye_rluns,
    check_fjdarye_sum,
    fjdarye_disks_printstates,
    fjdarye_disks_summary,
    inventory_fjdarye_disks,
    inventory_fjdarye_disks_summary,
    inventory_fjdarye_item,
    inventory_fjdarye_rluns,
    inventory_fjdarye_sum,
    parse_fjdarye_disks,
)
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import StringByteTable, StringTable

FjdaryeSection = Mapping[str, Mapping[str, Union[int, str]]]
FjdaryeCheckResult = Optional[tuple[int, str]]


@pytest.mark.parametrize(
    # Assumption: Section will always be a StringTable
    "section, discovery_result",
    [
        pytest.param(
            [
                ["0", "1"],
                ["1", "1"],
                ["2", "1"],
                ["3", "1"],
                ["4", "4"],
            ],
            [
                ("0", {}),
                ("1", {}),
                ("2", {}),
                ("3", {}),
            ],
            id="Discovers items from the raw section. Should only discover items that don't have a status equal to 4 (invalid)",
        ),
        pytest.param(
            [],
            [],
            id="If the raw section is an empty list, nothing is discovered",
        ),
    ],
)
def test_inventory_fjdarye_item(
    section: StringTable,
    discovery_result: Sequence[tuple[str, dict]],
) -> None:
    assert inventory_fjdarye_item(section) == discovery_result


@pytest.mark.parametrize(
    # The function is defined with _no_param, so the params will be an empty dict.
    # Assumption: Section will always be a StringTable
    # Assumption: The fjdarye_disks_status mapping consistantly gives us a tuple of (state, state_description)
    "section, item, check_result",
    [
        pytest.param(
            [
                ["0", "1"],
                ["1", "1"],
                ["2", "1"],
                ["3", "1"],
                ["4", "4"],
            ],
            "1",
            (0, "Normal"),
            id="If the given item is present in the raw section, the check result state and check summary are the mapped tuple from fjdarye_item_status",
        ),
        pytest.param(
            [],
            "4",
            None,
            id="If the raw section is empty, the check result is None",
        ),
        pytest.param(
            [
                ["0", "1"],
                ["1", "1"],
                ["2", "1"],
                ["3", "1"],
                ["4", "4"],
            ],
            "13",
            None,
            id="If the given item is not present in the raw section, the check result is None",
        ),
    ],
)
def test_check_fjdarye_item(
    section: StringTable,
    item: str,
    check_result: FjdaryeCheckResult,
) -> None:
    assert check_fjdarye_item(item, {}, section) == check_result


@pytest.mark.parametrize(
    # Assumption: The fjdarye_disks_status mapping consistantly gives us a tuple of (state, state_description)
    # Assumption: Section will always be a StringTable
    "section, parse_result",
    [
        pytest.param(
            [
                ["0", "1"],
                ["1", "1"],
                ["2", "1"],
                ["3", "1"],
                ["4", "4"],
            ],
            {
                "0": {"state": 0, "state_readable": "available", "state_disk": "1"},
                "1": {"state": 0, "state_readable": "available", "state_disk": "1"},
                "2": {"state": 0, "state_readable": "available", "state_disk": "1"},
                "3": {"state": 0, "state_readable": "available", "state_disk": "1"},
                "4": {"state": 1, "state_readable": "notsupported", "state_disk": "4"},
            },
            id="If disk_state is in the mapping, then the function should assign the state, state_readable and state_disk accordingly",
        ),
        pytest.param(
            [
                ["0", "1"],
                ["4", "4"],
                ["14", "14"],
            ],
            {
                "0": {"state": 0, "state_readable": "available", "state_disk": "1"},
                "4": {"state": 1, "state_readable": "notsupported", "state_disk": "4"},
                "14": {"state": 3, "state_readable": "unknown[14]", "state_disk": "14"},
            },
            id="If disk_state is not in the mapping, then the function should assign 3(UNKNOWN) to the state and unknown[disk_state] to state_readable and disk_state to state_disk",
        ),
        pytest.param(
            [],
            {},
            id="If the input is an empty list, the parsed section is an empty dictionary",
        ),
        pytest.param(
            [
                ["0", "1"],
                ["4", "4"],
                ["14", "14"],
                ["14", "1"],
            ],
            {
                "0": {"state": 0, "state_readable": "available", "state_disk": "1"},
                "4": {"state": 1, "state_readable": "notsupported", "state_disk": "4"},
                "14": {"state": 3, "state_readable": "unknown[14]", "state_disk": "14"},
            },
            id="If the parse function is trying to alter already existing elements in the parsed section it should not allow it and should keep the existing state",
        ),
    ],
)
def test_parse_fjdarye_disks(
    section: StringTable,
    parse_result: FjdaryeSection,
) -> None:
    assert parse_fjdarye_disks(section) == parse_result


@pytest.mark.parametrize(
    # Assumption: The fjdarye_disks_status mapping consistently gives us a tuple of (state, state_description)
    # Assumption: Section will always be a StringTable
    "section",
    [
        pytest.param(
            [
                ["0", "1", "3"],
                ["1", "1"],
                ["2", "1"],
                ["3", "1"],
                ["4", "4"],
            ],
            id="If info contains more than 2 elements, the parse function should raise a ValueError",
        ),
        pytest.param(
            [
                ["0"],
                ["1", "1"],
                ["2", "1"],
                ["3", "1"],
                ["4", "4"],
            ],
            id="If info contains less than 2 elements, the parse function should raise a ValueError",
        ),
    ],
)
def test_parse_fjdarye_disks_with_error_input(
    section: StringTable,
) -> None:
    with pytest.raises(ValueError):
        assert parse_fjdarye_disks(section)


@pytest.mark.parametrize(
    # Assumption: The input parameter type will be correct, because it's the output of a previously tested function
    "parsed, discovery_result",
    [
        pytest.param(
            {
                "0": {"state": 0, "state_readable": "available", "state_disk": "1"},
                "1": {"state": 0, "state_readable": "available", "state_disk": "1"},
                "2": {"state": 0, "state_readable": "available", "state_disk": "1"},
                "3": {"state": 0, "state_readable": "available", "state_disk": "1"},
                "4": {"state": 1, "state_readable": "notavailable", "state_disk": "3"},
            },
            [
                ("0", "'available'"),
                ("1", "'available'"),
                ("2", "'available'"),
                ("3", "'available'"),
            ],
            id="Should return (idx,state_description) of all disks that don't have a state_disk of 3",
        ),
        pytest.param(
            {},
            [],
            id="If the parsed section is empty, no items are discovered",
        ),
    ],
)
def test_inventory_fjdarye_disks(
    parsed: FjdaryeSection,
    discovery_result: Sequence[tuple[str, str]],
) -> None:
    assert inventory_fjdarye_disks(parsed) == discovery_result


@pytest.mark.parametrize(
    "parsed, item, params, check_result",
    [
        pytest.param(
            {
                "0": {"state": 0, "state_readable": "available", "state_disk": "1"},
                "1": {"state": 0, "state_readable": "available", "state_disk": "1"},
                "2": {"state": 0, "state_readable": "available", "state_disk": "1"},
                "3": {"state": 0, "state_readable": "available", "state_disk": "1"},
                "4": {"state": 1, "state_readable": "notavailable", "state_disk": "3"},
            },
            "5",
            {},
            None,
            id="If the given item can not be found in the provided section, check result is None",
        ),
        pytest.param(
            {
                "0": {"state": 0, "state_readable": "available", "state_disk": "1"},
                "3": {"state": 0, "state_readable": "available", "state_disk": "1"},
                "4": {"state": 1, "state_readable": "notavailable", "state_disk": "3"},
            },
            "4",
            {},
            (0, "Status: notavailable"),
            id="If expected_state and use_device_states are not configured, the check result state is OK and the summary is the readable state of the disk",
        ),
        pytest.param(
            {
                "0": {"state": 0, "state_readable": "available", "state_disk": "1"},
                "3": {"state": 0, "state_readable": "available", "state_disk": "1"},
                "4": {"state": 1, "state_readable": "notavailable", "state_disk": "3"},
            },
            "4",
            {"expected_state": "available"},
            (2, "Status: notavailable (expected: available)"),
            id="If only the expected_state parameter is configured and it doesn't match the current state of the disk, the result is a state of CRIT with a description indicating the difference between states",
        ),
        pytest.param(
            {
                "0": {"state": 0, "state_readable": "available", "state_disk": "1"},
                "3": {"state": 0, "state_readable": "available", "state_disk": "1"},
                "4": {"state": 1, "state_readable": "notavailable", "state_disk": "3"},
            },
            "4",
            {"use_device_states": True},
            (1, "Status: notavailable (use device states)"),
            id="If the use_device_states parameter is set to True, the function uses the current device state as the result. It also provides a note in the result that it's using it.",
        ),
        pytest.param(
            {
                "0": {"state": 0, "state_readable": "available", "state_disk": "1"},
                "3": {"state": 0, "state_readable": "available", "state_disk": "1"},
                "4": {"state": 1, "state_readable": "notavailable", "state_disk": "3"},
            },
            "4",
            {"expected_state": "available", "use_device_states": True},
            (1, "Status: notavailable (use device states)"),
            id="If both the use_device_states and expected_state are provided, the function uses the current device state as the result. Same behaviour as if the expected_state parameter was not provided.",
        ),
    ],
)
def test_check_fjdarye_disks(
    parsed: FjdaryeSection,
    item: str,
    params: Mapping,
    check_result: FjdaryeCheckResult,
) -> None:
    assert check_fjdarye_disks(item, params, parsed) == check_result


@pytest.mark.parametrize(
    # Assumption: The input parameter type will be correct, because it's the output of a previously tested function
    "parsed, summary_result",
    [
        pytest.param(
            {},
            {},
            id="If the section is empty, no summary is shown",
        ),
        pytest.param(
            {
                "0": {"state": 0, "state_readable": "available", "state_disk": "1"},
                "1": {"state": 0, "state_readable": "available", "state_disk": "1"},
                "2": {"state": 0, "state_readable": "available", "state_disk": "1"},
                "3": {"state": 0, "state_readable": "available", "state_disk": "1"},
                "5": {"state": 1, "state_readable": "notavailable", "state_disk": "2"},
            },
            {"available": 4, "notavailable": 1},
            id="Return a summary of the names of states and a count of how many times they appear.",
        ),
        pytest.param(
            {
                "0": {"state": 0, "state_readable": "available", "state_disk": "1"},
                "1": {"state": 0, "state_readable": "available", "state_disk": "1"},
                "4": {"state": 1, "state_readable": "notavailable", "state_disk": "3"},
                "5": {"state": 1, "state_readable": "notavailable", "state_disk": "2"},
            },
            {"available": 2, "notavailable": 1},
            id="Return a summary of the names of states and a count of how many times they appear, not including disks with state_disk=3",
        ),
    ],
)
def test_fjdarye_disks_summary(
    parsed: FjdaryeSection,
    summary_result: Mapping[str, int],
) -> None:
    assert fjdarye_disks_summary(parsed) == summary_result


@pytest.mark.parametrize(
    "parsed, inventory_summary_result",
    [
        pytest.param(
            {},
            [],
            id="If the section is empty, no items are discovered",
        ),
        pytest.param(
            {
                "0": {"state": 0, "state_readable": "available", "state_disk": "1"},
                "1": {"state": 0, "state_readable": "available", "state_disk": "1"},
                "2": {"state": 0, "state_readable": "available", "state_disk": "1"},
                "3": {"state": 0, "state_readable": "available", "state_disk": "1"},
            },
            [(None, {"available": 4})],
            id="Discovers a service without item and discovery parameters, which indicates the current device states.",
        ),
        pytest.param(
            {
                "0": {"state": 0, "state_readable": "available", "state_disk": "1"},
                "1": {"state": 0, "state_readable": "available", "state_disk": "1"},
                "4": {"state": 1, "state_readable": "notavailable", "state_disk": "3"},
            },
            [(None, {"available": 2})],
            id="Discovers a service without item and discovery parameters, which indicates the current device states. The summary does not include disks with state_disk=3",
        ),
    ],
)
def test_inventory_fjdarye_disks_summary(
    parsed: FjdaryeSection,
    inventory_summary_result: Sequence[tuple[None, Mapping[str, int]]],
) -> None:
    assert inventory_fjdarye_disks_summary(parsed) == inventory_summary_result


@pytest.mark.parametrize(
    # Assumption: The input parameter type will be correct, because it's the output of a previously tested function
    "states, formatted_summary_result",
    [
        pytest.param(
            {"available": 4, "notavailable": 1},
            "Available: 4, Notavailable: 1",
            id="Returns a formatted string of the summary of disk states (output of the fjdarye_disks_summary function)",
        ),
    ],
)
def test_fjdarye_disks_printstates(
    states: Mapping[str, int],
    formatted_summary_result: str,
) -> None:
    assert fjdarye_disks_printstates(states) == formatted_summary_result


@pytest.mark.parametrize(
    # Assumption: The map_states will always return a int
    # Assumption: Since the input is the result of the parse function and the function is previously tested, we assume it will always be correct
    # Assumption: Since current_state is a result of a previously tested function, we assume it will always be a dict that contains all necessary information
    # Assumption: It's same for infotext as for current_state
    "parsed, params, check_result",
    [
        pytest.param(
            {
                "0": {"state": 0, "state_readable": "available", "state_disk": "1"},
                "3": {"state": 2, "state_readable": "broken", "state_disk": "2"},
                "4": {"state": 1, "state_readable": "notsupported", "state_disk": "4"},
            },
            {"available": 1, "broken": 1, "notsupported": 1, "use_device_states": False},
            (0, "Available: 1, Broken: 1, Notsupported: 1"),
            id="If the number of disks in a specific state is equal to the expected number and use_device_state is not configured, the check result state is OK",
        ),
        pytest.param(
            {
                "0": {"state": 0, "state_readable": "available", "state_disk": "1"},
                "3": {"state": 2, "state_readable": "broken", "state_disk": "2"},
                "4": {"state": 1, "state_readable": "notsupported", "state_disk": "4"},
            },
            {"available": 2, "broken": 1, "notsupported": 1, "use_device_states": False},
            (
                2,
                "Available: 1, Broken: 1, Notsupported: 1 (expected: Available: 2, Broken: 1, Notsupported: 1)",
            ),
            id="If the number of disks in a specific state is lower than the expected number and use_device_state is not configured, the check result is CRIT",
        ),
        pytest.param(
            {
                "0": {"state": 0, "state_readable": "available", "state_disk": "1"},
                "1": {"state": 0, "state_readable": "available", "state_disk": "1"},
                "3": {"state": 2, "state_readable": "broken", "state_disk": "2"},
                "4": {"state": 1, "state_readable": "notsupported", "state_disk": "4"},
            },
            {"available": 1, "broken": 1, "notsupported": 1, "use_device_states": False},
            (
                1,
                "Available: 2, Broken: 1, Notsupported: 1 (expected: Available: 1, Broken: 1, Notsupported: 1)",
            ),
            id="If the number of disks in a specific state is higher than the expected number and use_device_state is not configured, the check result is WARN",
        ),
        pytest.param(
            {
                "0": {"state": 0, "state_readable": "available", "state_disk": "1"},
                "3": {"state": 2, "state_readable": "broken", "state_disk": "2"},
                "4": {"state": 1, "state_readable": "notsupported", "state_disk": "4"},
            },
            {
                "available": 1,
                "broken": 1,
                "notsupported": 1,
                "use_device_states": True,
            },
            (2, "Available: 1, Broken: 1, Notsupported: 1 (ignore expected state)"),
            id="If use_device_states is set to True, the check result state is the max mapped value from the map_states mapping (worst state of the selected disks).",
        ),
    ],
)
def test_check_fjdarye_disks_summary(
    parsed: FjdaryeSection,
    params: Mapping[str, Union[int, bool]],
    check_result: tuple[int, str],
) -> None:
    assert check_fjdarye_disks_summary(index=None, params=params, parsed=parsed) == check_result


@pytest.mark.parametrize(
    "section, inventory_result",
    [
        pytest.param(
            [
                [
                    "0",
                    "\x00\x00\x00\xa0\x10\x10\x00\x00\x03\x00\x00\x00\x00ÿÿÿ\x00\x00@Í\x04\x00\x00\x00\x00\x06\x00\x00\x00\x06\x00\x00\x00\x00\x00\x00\x01 @@\x0f\x01\x01\x022\x00\x00\x00\x02\x00\x00\x01",
                    # The value above corresponds to: '0.0.0.160.16.16.0.0.3.0.0.0.0.255.255.255.0.0.64.205.4.0.0.0.0.6.0.0.0.6.0.0.0.0.0.0.1.32.64.64.15.1.1.2.50.0.0.0.2.0.0.1'
                ],
            ],
            [("0", "", None)],
            id="Because the value of the fourth byte is '\xa0'(160) RLUN is present and a service is discovered. The item name is the first element of the raw section (index).",
        ),
        pytest.param(
            [
                [
                    "1",
                    "\x01\x00\x03\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00ÿÿÿ\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00",
                    # The value above correspond to: '1.0.3.0.0.0.0.0.0.0.0.0.0.255.255.255.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.1.0.1.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0'
                ],
            ],
            [],
            id="RLUN is not present and no service is discovered, because the value of the fourth byte is not '\xa0'(160) ",
        ),
    ],
)
def test_inventory_fjdarye_rluns(
    section: StringByteTable,
    inventory_result: Sequence[tuple[str, str, None]],
) -> None:
    assert list(inventory_fjdarye_rluns(section)) == inventory_result


@pytest.mark.parametrize(
    "section, item, rluns_check_result",
    [
        pytest.param(
            [
                [
                    "0",
                    "\x00\x00\x00\xa0\x10\x10\x00\x00\x03\x00\x00\x00\x00ÿÿÿ\x00\x00@Í\x04\x00\x00\x00\x00\x06\x00\x00\x00\x06\x00\x00\x00\x00\x00\x00\x01 @@\x0f\x01\x01\x022\x00\x00\x00\x02\x00\x00\x01",
                    # The value above corresponds to: '0.0.0.160.16.16.0.0.3.0.0.0.0.255.255.255.0.0.64.205.4.0.0.0.0.6.0.0.0.6.0.0.0.0.0.0.1.32.64.64.15.1.1.2.50.0.0.0.2.0.0.1'
                ],
            ],
            "2",
            None,
            id="If the item is not in the section, the check result is None",
        ),
        pytest.param(
            [
                [
                    "0",
                    "\x00\x00\x00\x00\x10\x10\x00\x00\x03\x00\x00\x00\x00ÿÿÿ\x00\x00@Í\x04\x00\x00\x00\x00\x06\x00\x00\x00\x06\x00\x00\x00\x00\x00\x00\x01 @@\x0f\x01\x01\x022\x00\x00\x00\x02\x00\x00\x01",
                    # The value above correspond to: '0.0.0.0.16.16.0.0.3.0.0.0.0.255.255.255.0.0.64.205.4.0.0.0.0.6.0.0.0.6.0.0.0.0.0.0.1.32.64.64.15.1.1.2.50.0.0.0.2.0.0.1'
                ],
            ],
            "0",
            (2, "RLUN is not present"),
            id="If the fourth byte is not equal to '\xa0'(160), RLUN is not present and check result state is CRIT",
        ),
        pytest.param(
            [
                [
                    "0",
                    "\x00\x00\x08\xa0\x10\x10\x00\x00\x03\x00\x00\x00\x00ÿÿÿ\x00\x00@Í\x04\x00\x00\x00\x00\x06\x00\x00\x00\x06\x00\x00\x00\x00\x00\x00\x01 @@\x0f\x01\x01\x022\x00\x00\x00\x02\x00\x00\x01",
                    # The value above correspond to: '0.0.8.160.16.16.0.0.3.0.0.0.0.255.255.255.0.0.64.205.4.0.0.0.0.6.0.0.0.6.0.0.0.0.0.0.1.32.64.64.15.1.1.2.50.0.0.0.2.0.0.1'
                ],
            ],
            "0",
            (1, "RLUN is rebuilding"),
            id="If the third byte is equal to '\x08'(8), RLUN is rebuilding and result state is WARN",
        ),
        pytest.param(
            [
                [
                    "0",
                    "\x00\x00\x07\xa0\x10\x10\x00\x00\x03\x00\x00\x00\x00ÿÿÿ\x00\x00@Í\x04\x00\x00\x00\x00\x06\x00\x00\x00\x06\x00\x00\x00\x00\x00\x00\x01 @@\x0f\x01\x01\x022\x00\x00\x00\x02\x00\x00\x01",
                    # The value above correspond to: '0.0.7.160.16.16.0.0.3.0.0.0.0.255.255.255.0.0.64.205.4.0.0.0.0.6.0.0.0.6.0.0.0.0.0.0.1.32.64.64.15.1.1.2.50.0.0.0.2.0.0.1'
                ],
            ],
            "0",
            (1, "RLUN copyback in progress"),
            id="If the third byte is equal to '\x07'(7), RLUN copyback is in progress and result state is WARN",
        ),
        pytest.param(
            [
                [
                    "0",
                    "\x00\x00\x41\xa0\x10\x10\x00\x00\x03\x00\x00\x00\x00ÿÿÿ\x00\x00@Í\x04\x00\x00\x00\x00\x06\x00\x00\x00\x06\x00\x00\x00\x00\x00\x00\x01 @@\x0f\x01\x01\x022\x00\x00\x00\x02\x00\x00\x01",
                    # The value above correspond to: '0.0.65.160.16.16.0.0.3.0.0.0.0.255.255.255.0.0.64.205.4.0.0.0.0.6.0.0.0.6.0.0.0.0.0.0.1.32.64.64.15.1.1.2.50.0.0.0.2.0.0.1'
                ],
            ],
            "0",
            (1, "RLUN spare is in use"),
            id="If the third byte is equal to '\x41'(65), RLUN spare is in use and result state is WARN",
        ),
        pytest.param(
            [
                [
                    "0",
                    "\x00\x00\x42\xa0\x10\x10\x00\x00\x03\x00\x00\x00\x00ÿÿÿ\x00\x00@Í\x04\x00\x00\x00\x00\x06\x00\x00\x00\x06\x00\x00\x00\x00\x00\x00\x01 @@\x0f\x01\x01\x022\x00\x00\x00\x02\x00\x00\x01",
                    # The value above correspond to: '0.0.66.160.16.16.0.0.3.0.0.0.0.255.255.255.0.0.64.205.4.0.0.0.0.6.0.0.0.6.0.0.0.0.0.0.1.32.64.64.15.1.1.2.50.0.0.0.2.0.0.1'
                ],
            ],
            "0",
            (0, "RLUN is in RAID0 state"),
            id="If the third byte is equal to '\x42'(66), RLUN is in RAID0 state and result state is OK",
        ),
        pytest.param(
            [
                [
                    "0",
                    "\x00\x00\x00\xa0\x10\x10\x00\x00\x03\x00\x00\x00\x00ÿÿÿ\x00\x00@Í\x04\x00\x00\x00\x00\x06\x00\x00\x00\x06\x00\x00\x00\x00\x00\x00\x01 @@\x0f\x01\x01\x022\x00\x00\x00\x02\x00\x00\x01",
                    # The value above correspond to: '0.0.0.160.16.16.0.0.3.0.0.0.0.255.255.255.0.0.64.205.4.0.0.0.0.6.0.0.0.6.0.0.0.0.0.0.1.32.64.64.15.1.1.2.50.0.0.0.2.0.0.1'
                ],
            ],
            "0",
            (0, "RLUN is in normal state"),
            id="If the third byte is equal to '\x00'(0), RLUN is in normal state and result state is OK",
        ),
        pytest.param(
            [
                [
                    "0",
                    "\x00\x00\x44\xa0\x10\x10\x00\x00\x03\x00\x00\x00\x00ÿÿÿ\x00\x00@Í\x04\x00\x00\x00\x00\x06\x00\x00\x00\x06\x00\x00\x00\x00\x00\x00\x01 @@\x0f\x01\x01\x022\x00\x00\x00\x02\x00\x00\x01",
                    # The value above correspond to: '0.0.68.160.16.16.0.0.3.0.0.0.0.255.255.255.0.0.64.205.4.0.0.0.0.6.0.0.0.6.0.0.0.0.0.0.1.32.64.64.15.1.1.2.50.0.0.0.2.0.0.1'
                ],
            ],
            "0",
            (2, "RLUN in unknown state 44"),
            id="If RLUN is present and none of the above criteria are met, the RLUN state is uknown and the result state is CRIT",
        ),
    ],
)
def test_check_fjdarye_rluns(
    section: StringByteTable,
    item: str,
    rluns_check_result: FjdaryeCheckResult,
) -> None:
    assert check_fjdarye_rluns(item, {}, section) == rluns_check_result


@pytest.mark.parametrize(
    "section, inventory_sum_result",
    [
        pytest.param(
            [["3"]],
            [("0", {})],
            id="If the length of the input section is 1, a service with name '0' is discovered.",
        ),
        pytest.param(
            [["3", "4"]],
            [],
            id="If the length of the input section is not 1, no services are discovered",
        ),
    ],
)
def test_inventory_fjdarye_sum(
    section: StringTable,
    inventory_sum_result: Sequence[tuple[str, Mapping]],
) -> None:
    assert list(inventory_fjdarye_sum(section)) == inventory_sum_result


@pytest.mark.parametrize(
    "section, inventory_sum_result",
    [
        pytest.param(
            [],
            [],
            id="If the length of the input section is 0, an IndexError is raised",
        ),
    ],
)
def test_inventory_fjdarye_sum_with_error(
    section: StringTable,
    inventory_sum_result: Sequence[tuple[str, Mapping]],
) -> None:
    with pytest.raises(IndexError):
        assert list(inventory_fjdarye_sum(section)) == inventory_sum_result


@pytest.mark.parametrize(
    "section, check_sum_result",
    [
        pytest.param(
            [["3", "4"]],
            (3, "No status summary present"),
            id="If the length of the input is not 1, the check result state is UNKNOWN",
        ),
        pytest.param(
            [["3"]],
            (0, "Status is ok"),
            id="If the summary status is equal to 3, the check result state is OK",
        ),
        pytest.param(
            [["4"]],
            (1, "Status is warning"),
            id="If the summary status is equal 4, the check result state is WARN",
        ),
        pytest.param(
            [["5"]],
            (2, "Status is failed"),
            id="If the summary status is 1 or 2 or 5, the check result state is WARN and the description is the corresponding value from the fjdarye_sum_status mapping",
        ),
    ],
)
def test_check_fjdarye_sum(
    section: StringTable,
    check_sum_result: tuple[int, str],
) -> None:
    assert check_fjdarye_sum(None, {}, section) == check_sum_result
