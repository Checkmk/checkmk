#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Any, Mapping, Optional, Sequence

import pytest

from cmk.base.check_legacy_includes.fjdarye import (
    _fjdarye_disks_states_summary,
    check_fjdarye_disks,
    check_fjdarye_disks_summary,
    check_fjdarye_rluns,
    check_fjdarye_sum,
    discover_fjdarye_disks,
    discover_fjdarye_disks_summary,
    discover_fjdarye_rluns,
    discover_fjdarye_sum,
    FjdaryeDeviceStatus,
    FjdaryeDisk,
    FjdaryeRlun,
    parse_fjdarye_disks,
    parse_fjdarye_rluns,
    parse_fjdarye_sum,
    SectionFjdaryeDisk,
)
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import StringTable

FjdaryeSection = Mapping[str, Mapping[str, int | str]]
FjdaryeCheckResult = Sequence[tuple[int, str]]


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
                "0": FjdaryeDisk(
                    disk_index="0", state=0, state_description="available", state_disk="1"
                ),
                "1": FjdaryeDisk(
                    disk_index="1", state=0, state_description="available", state_disk="1"
                ),
                "2": FjdaryeDisk(
                    disk_index="2", state=0, state_description="available", state_disk="1"
                ),
                "3": FjdaryeDisk(
                    disk_index="3", state=0, state_description="available", state_disk="1"
                ),
                "4": FjdaryeDisk(
                    disk_index="4", state=1, state_description="notsupported", state_disk="4"
                ),
            },
            id="Returns disk information based on the disk_state attribute",
        ),
        pytest.param(
            [
                ["0", "1"],
                ["4", "4"],
                ["14", "14"],
            ],
            {
                "0": FjdaryeDisk(
                    disk_index="0", state=0, state_description="available", state_disk="1"
                ),
                "4": FjdaryeDisk(
                    disk_index="4", state=1, state_description="notsupported", state_disk="4"
                ),
                "14": FjdaryeDisk(
                    disk_index="14", state=3, state_description="unknown[14]", state_disk="14"
                ),
            },
            id="If disk_state is not in the mapping, then the function should assign 3(UNKNOWN) to the state and unknown[disk_state] to state_description and disk_state to state_disk",
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
                "0": FjdaryeDisk(
                    disk_index="0", state=0, state_description="available", state_disk="1"
                ),
                "4": FjdaryeDisk(
                    disk_index="4", state=1, state_description="notsupported", state_disk="4"
                ),
                "14": FjdaryeDisk(
                    disk_index="14", state=3, state_description="unknown[14]", state_disk="14"
                ),
            },
            id="If the parse function is trying to alter already existing elements in the parsed section it should not allow it and should keep the existing state",
        ),
    ],
)
def test_parse_fjdarye_disks(
    section: StringTable,
    parse_result: SectionFjdaryeDisk,
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
                "0": FjdaryeDisk(
                    disk_index="0", state=0, state_description="available", state_disk="1"
                ),
                "1": FjdaryeDisk(
                    disk_index="1", state=0, state_description="available", state_disk="1"
                ),
                "2": FjdaryeDisk(
                    disk_index="2", state=0, state_description="available", state_disk="1"
                ),
                "3": FjdaryeDisk(
                    disk_index="3", state=0, state_description="available", state_disk="1"
                ),
                "4": FjdaryeDisk(
                    disk_index="4", state=1, state_description="notsupported", state_disk="3"
                ),
            },
            [
                ("0", "available"),
                ("1", "available"),
                ("2", "available"),
                ("3", "available"),
            ],
            id="Should return (disk_index,state_description) of all disks that don't have a state_disk of 3",
        ),
        pytest.param(
            {},
            [],
            id="If the parsed section is empty, no items are discovered",
        ),
    ],
)
def test_discover_fjdarye_disks(
    parsed: SectionFjdaryeDisk,
    discovery_result: Sequence[tuple[str, str]],
) -> None:
    assert list(discover_fjdarye_disks(parsed)) == discovery_result


@pytest.mark.parametrize(
    "section, item, params, check_result",
    [
        pytest.param(
            {
                "0": FjdaryeDisk(
                    disk_index="0", state=0, state_description="available", state_disk="1"
                ),
                "1": FjdaryeDisk(
                    disk_index="1", state=0, state_description="available", state_disk="1"
                ),
                "2": FjdaryeDisk(
                    disk_index="2", state=0, state_description="available", state_disk="1"
                ),
                "3": FjdaryeDisk(
                    disk_index="3", state=0, state_description="available", state_disk="1"
                ),
                "4": FjdaryeDisk(
                    disk_index="4", state=1, state_description="notavailable", state_disk="3"
                ),
            },
            "5",
            {},
            [],
            id="If the given item can not be found in the provided section, check result is an empty list.",
        ),
        pytest.param(
            {
                "0": FjdaryeDisk(
                    disk_index="0", state=0, state_description="available", state_disk="1"
                ),
                "1": FjdaryeDisk(
                    disk_index="1", state=0, state_description="available", state_disk="1"
                ),
                "2": FjdaryeDisk(
                    disk_index="2", state=0, state_description="available", state_disk="1"
                ),
                "3": FjdaryeDisk(
                    disk_index="3", state=0, state_description="available", state_disk="1"
                ),
                "4": FjdaryeDisk(
                    disk_index="4", state=1, state_description="notavailable", state_disk="3"
                ),
            },
            "3",
            "available",
            [(0, "Status: available")],
            id="If no rules are configured, the expected_state of the disk is its state_description at the time it was discovered.",
        ),
        pytest.param(
            {
                "0": FjdaryeDisk(
                    disk_index="0", state=0, state_description="available", state_disk="1"
                ),
                "1": FjdaryeDisk(
                    disk_index="1", state=0, state_description="available", state_disk="1"
                ),
                "2": FjdaryeDisk(
                    disk_index="2", state=0, state_description="available", state_disk="1"
                ),
                "3": FjdaryeDisk(
                    disk_index="3", state=0, state_description="available", state_disk="1"
                ),
                "4": FjdaryeDisk(
                    disk_index="4", state=1, state_description="notavailable", state_disk="3"
                ),
            },
            "4",
            {},
            [(0, "Status: notavailable")],
            id="If a rule with no parameters is created, the state is OK and the summary is the device's status description.",
        ),
        pytest.param(
            {
                "0": FjdaryeDisk(
                    disk_index="0", state=0, state_description="available", state_disk="1"
                ),
                "1": FjdaryeDisk(
                    disk_index="1", state=0, state_description="available", state_disk="1"
                ),
                "2": FjdaryeDisk(
                    disk_index="2", state=0, state_description="available", state_disk="1"
                ),
                "3": FjdaryeDisk(
                    disk_index="3", state=0, state_description="available", state_disk="1"
                ),
                "4": FjdaryeDisk(
                    disk_index="4", state=1, state_description="notavailable", state_disk="3"
                ),
            },
            "4",
            {"expected_state": "available"},
            [(2, "Status: notavailable (expected: available)")],
            id="If only the expected_state parameter is configured in the ruleset and it doesn't match the current state of the disk, the result is a state of CRIT with a description indicating the difference between states.",
        ),
        pytest.param(
            {
                "0": FjdaryeDisk(
                    disk_index="0", state=0, state_description="available", state_disk="1"
                ),
                "1": FjdaryeDisk(
                    disk_index="1", state=0, state_description="available", state_disk="1"
                ),
                "2": FjdaryeDisk(
                    disk_index="2", state=0, state_description="available", state_disk="1"
                ),
                "3": FjdaryeDisk(
                    disk_index="3", state=0, state_description="available", state_disk="1"
                ),
                "4": FjdaryeDisk(
                    disk_index="4", state=1, state_description="notavailable", state_disk="3"
                ),
            },
            "3",
            {"expected_state": "available"},
            [(0, "Status: available")],
            id="If only the expected_state parameter is configured in the ruleset and it matches the current state of the disk, the result is a state of OK with a summary indicating the state of the disk.",
        ),
        pytest.param(
            {
                "0": FjdaryeDisk(
                    disk_index="0", state=0, state_description="available", state_disk="1"
                ),
                "1": FjdaryeDisk(
                    disk_index="1", state=0, state_description="available", state_disk="1"
                ),
                "2": FjdaryeDisk(
                    disk_index="2", state=0, state_description="available", state_disk="1"
                ),
                "3": FjdaryeDisk(
                    disk_index="3", state=0, state_description="available", state_disk="1"
                ),
                "4": FjdaryeDisk(
                    disk_index="4", state=1, state_description="notavailable", state_disk="3"
                ),
            },
            "4",
            {"use_device_states": True},
            [(1, "Status: notavailable (using device states)")],
            id="If the use_device_states parameter is configures to True in the ruleset, the function uses the current device state as the result. It also provides a note in the result that it's using it.",
        ),
        pytest.param(
            {
                "0": FjdaryeDisk(
                    disk_index="0", state=0, state_description="available", state_disk="1"
                ),
                "1": FjdaryeDisk(
                    disk_index="1", state=0, state_description="available", state_disk="1"
                ),
                "2": FjdaryeDisk(
                    disk_index="2", state=0, state_description="available", state_disk="1"
                ),
                "3": FjdaryeDisk(
                    disk_index="3", state=0, state_description="available", state_disk="1"
                ),
                "4": FjdaryeDisk(
                    disk_index="4", state=1, state_description="notavailable", state_disk="3"
                ),
            },
            "4",
            {"use_device_states": False},
            [(0, "Status: notavailable")],
            id="If the use_device_states parameter is configures to False in the ruleset, the expected_state of the disk is its state_description at the time it was discovered. Basically, the behaviour is the same as if the parameter use_device_state wasn't even configured.",
        ),
        pytest.param(
            {
                "0": FjdaryeDisk(
                    disk_index="0", state=0, state_description="available", state_disk="1"
                ),
                "1": FjdaryeDisk(
                    disk_index="1", state=0, state_description="available", state_disk="1"
                ),
                "2": FjdaryeDisk(
                    disk_index="2", state=0, state_description="available", state_disk="1"
                ),
                "3": FjdaryeDisk(
                    disk_index="3", state=0, state_description="available", state_disk="1"
                ),
                "4": FjdaryeDisk(
                    disk_index="4", state=1, state_description="notavailable", state_disk="3"
                ),
            },
            "4",
            {"expected_state": "available", "use_device_states": True},
            [(1, "Status: notavailable (using device states)")],
            id="If both the use_device_states and expected_state are configured in the ruleset, the function uses the current device state as the result. Same behaviour as if the expected_state parameter was not configured.",
        ),
        pytest.param(
            {
                "0": FjdaryeDisk(
                    disk_index="0", state=0, state_description="available", state_disk="1"
                ),
                "1": FjdaryeDisk(
                    disk_index="1", state=0, state_description="available", state_disk="1"
                ),
                "2": FjdaryeDisk(
                    disk_index="2", state=0, state_description="available", state_disk="1"
                ),
                "3": FjdaryeDisk(
                    disk_index="3", state=0, state_description="available", state_disk="1"
                ),
                "4": FjdaryeDisk(
                    disk_index="4", state=1, state_description="notavailable", state_disk="3"
                ),
            },
            "4",
            {"expected_state": "available", "use_device_states": False},
            [(2, "Status: notavailable (expected: available)")],
            id="If use_device_states is configured to False and expected_state is configured in the ruleset, the behaviour is as if only the expected_state was configured.",
        ),
    ],
)
def test_check_fjdarye_disks(
    section: SectionFjdaryeDisk,
    item: str,
    params: Mapping[str, Any] | str,
    check_result: FjdaryeCheckResult,
) -> None:
    assert list(check_fjdarye_disks(item, params, section)) == check_result


@pytest.mark.parametrize(
    # Assumption: The input parameter type will be correct, because it's the output of a previously tested function
    "section, summary_result",
    [
        pytest.param(
            {},
            {},
            id="If the section is empty, no summary is shown",
        ),
        pytest.param(
            {
                "0": FjdaryeDisk(
                    disk_index="0", state=0, state_description="available", state_disk="1"
                ),
                "1": FjdaryeDisk(
                    disk_index="1", state=0, state_description="available", state_disk="1"
                ),
                "2": FjdaryeDisk(
                    disk_index="2", state=0, state_description="available", state_disk="1"
                ),
                "3": FjdaryeDisk(
                    disk_index="3", state=0, state_description="available", state_disk="1"
                ),
                "4": FjdaryeDisk(
                    disk_index="4", state=1, state_description="notavailable", state_disk="4"
                ),
            },
            {"available": 4, "notavailable": 1},
            id="Return a summary of the names of states and a count of how many times they appear.",
        ),
        pytest.param(
            {
                "0": FjdaryeDisk(
                    disk_index="0", state=0, state_description="available", state_disk="1"
                ),
                "1": FjdaryeDisk(
                    disk_index="1", state=0, state_description="available", state_disk="1"
                ),
                "2": FjdaryeDisk(
                    disk_index="2", state=0, state_description="available", state_disk="3"
                ),
                "4": FjdaryeDisk(
                    disk_index="4", state=1, state_description="notavailable", state_disk="4"
                ),
            },
            {"available": 2, "notavailable": 1},
            id="Return a summary of the names of states and a count of how many times they appear, not including disks with state_disk=3",
        ),
    ],
)
def test_fjdarye_disks_states_summary(
    section: SectionFjdaryeDisk,
    summary_result: Mapping[str, int],
) -> None:
    assert _fjdarye_disks_states_summary(section) == summary_result


@pytest.mark.parametrize(
    "section, inventory_summary_result",
    [
        pytest.param(
            {},
            [],
            id="If the section is empty, no items are discovered",
        ),
        pytest.param(
            {
                "0": FjdaryeDisk(
                    disk_index="0", state=0, state_description="available", state_disk="1"
                ),
                "1": FjdaryeDisk(
                    disk_index="1", state=0, state_description="available", state_disk="1"
                ),
                "2": FjdaryeDisk(
                    disk_index="2", state=0, state_description="available", state_disk="1"
                ),
                "3": FjdaryeDisk(
                    disk_index="3", state=0, state_description="available", state_disk="1"
                ),
                "4": FjdaryeDisk(
                    disk_index="4", state=1, state_description="notavailable", state_disk="3"
                ),
            },
            [(None, {"available": 4})],
            id="Discovers a service without item and discovery parameters, which indicates the current device states.",
        ),
        pytest.param(
            {
                "0": FjdaryeDisk(
                    disk_index="0", state=0, state_description="available", state_disk="1"
                ),
                "1": FjdaryeDisk(
                    disk_index="1", state=0, state_description="available", state_disk="1"
                ),
                "4": FjdaryeDisk(
                    disk_index="4", state=1, state_description="notavailable", state_disk="3"
                ),
            },
            [(None, {"available": 2})],
            id="Discovers a service without item and discovery parameters, which indicates the current device states. The summary does not include disks with state_disk=3",
        ),
    ],
)
def test_discover_fjdarye_disks_summary(
    section: SectionFjdaryeDisk,
    inventory_summary_result: Sequence[tuple[None, Mapping[str, int]]],
) -> None:
    assert list(discover_fjdarye_disks_summary(section)) == inventory_summary_result


@pytest.mark.parametrize(
    # Assumption: The map_states will always return a int
    # Assumption: Since the input is the result of the parse function and the function is previously tested, we assume it will always be correct
    # Assumption: Since current_state is a result of a previously tested function, we assume it will always be a dict that contains all necessary information
    # Assumption: It's same for infotext as for current_state
    "section, params, check_result",
    [
        pytest.param(
            {
                "0": FjdaryeDisk(
                    disk_index="0", state=0, state_description="available", state_disk="1"
                ),
                "3": FjdaryeDisk(
                    disk_index="1", state=2, state_description="broken", state_disk="2"
                ),
                "4": FjdaryeDisk(
                    disk_index="4", state=1, state_description="notsupported", state_disk="4"
                ),
            },
            {"available": 1, "broken": 1, "notsupported": 1},
            [(0, "Available: 1, Broken: 1, Notsupported: 1")],
            id="If the number of disks in a specific state is equal to the expected number and use_device_state is not configured, the check result state is OK",
        ),
        pytest.param(
            {
                "0": FjdaryeDisk(
                    disk_index="0", state=0, state_description="available", state_disk="1"
                ),
                "3": FjdaryeDisk(
                    disk_index="1", state=2, state_description="broken", state_disk="2"
                ),
                "4": FjdaryeDisk(
                    disk_index="4", state=1, state_description="notsupported", state_disk="4"
                ),
            },
            {"available": 2, "broken": 1, "notsupported": 1, "use_device_states": False},
            [
                (
                    2,
                    "Available: 1, Broken: 1, Notsupported: 1 (expected: Available: 2, Broken: 1, Notsupported: 1)",
                )
            ],
            id="If the number of disks in a specific state is lower than the expected number and use_device_state is not configured, the check result is CRIT",
        ),
        pytest.param(
            {
                "0": FjdaryeDisk(
                    disk_index="0", state=0, state_description="available", state_disk="1"
                ),
                "1": FjdaryeDisk(
                    disk_index="1", state=0, state_description="available", state_disk="1"
                ),
                "3": FjdaryeDisk(
                    disk_index="1", state=2, state_description="broken", state_disk="2"
                ),
                "4": FjdaryeDisk(
                    disk_index="4", state=1, state_description="notsupported", state_disk="4"
                ),
            },
            {"available": 1, "broken": 1, "notsupported": 1, "use_device_states": False},
            [
                (
                    1,
                    "Available: 2, Broken: 1, Notsupported: 1 (expected: Available: 1, Broken: 1, Notsupported: 1)",
                )
            ],
            id="If the number of disks in a specific state is higher than the expected number and use_device_state is not configured, the check result is WARN",
        ),
        pytest.param(
            {
                "0": FjdaryeDisk(
                    disk_index="0", state=0, state_description="available", state_disk="1"
                ),
                "3": FjdaryeDisk(
                    disk_index="1", state=2, state_description="broken", state_disk="2"
                ),
                "4": FjdaryeDisk(
                    disk_index="4", state=1, state_description="notsupported", state_disk="4"
                ),
            },
            {
                "available": 1,
                "broken": 1,
                "notsupported": 1,
                "use_device_states": True,
            },
            [(2, "Available: 1, Broken: 1, Notsupported: 1 (using device states)")],
            id="If use_device_states is set to True, the check result state is the max mapped value from the map_states mapping (worst state of the selected disks).",
        ),
        pytest.param(
            {
                "0": FjdaryeDisk(
                    disk_index="0", state=0, state_description="available", state_disk="1"
                ),
                "3": FjdaryeDisk(
                    disk_index="1", state=2, state_description="broken", state_disk="2"
                ),
                "4": FjdaryeDisk(
                    disk_index="4", state=1, state_description="notsupported", state_disk="4"
                ),
                "14": FjdaryeDisk(
                    disk_index="14", state=3, state_description="unknown[14]", state_disk="14"
                ),
            },
            {
                "available": 1,
                "broken": 1,
                "notsupported": 1,
                "notpresent": 1,
                "use_device_states": True,
            },
            [
                (
                    3,
                    "Available: 1, Broken: 1, Notsupported: 1, Unknown[14]: 1 (using device states)",
                )
            ],
            id="If use_device_states is set to True and the state can't be mapped, the result state is UNKNOWN.",
        ),
    ],
)
def test_check_fjdarye_disks_summary(
    section: SectionFjdaryeDisk,
    params: Mapping[str, int | bool],
    check_result: FjdaryeCheckResult,
) -> None:
    assert (
        list(check_fjdarye_disks_summary(_item="", params=params, section=section)) == check_result
    )


@pytest.mark.parametrize(
    "section, parse_result",
    [
        pytest.param(
            [],
            {},
            id="The raw section is empty, so nothing is parsed",
        ),
        pytest.param(
            [
                [
                    "0",
                    "\x00\x00\x00\xa0\x10\x10\x00\x00\x03\x00\x00\x00\x00ÿÿÿ\x00\x00@Í\x04\x00\x00\x00\x00\x06\x00\x00\x00\x06\x00\x00\x00\x00\x00\x00\x01 @@\x0f\x01\x01\x022\x00\x00\x00\x02\x00\x00\x01",
                    # The value above corresponds to: '0.0.0.160.16.16.0.0.3.0.0.0.0.255.255.255.0.0.64.205.4.0.0.0.0.6.0.0.0.6.0.0.0.0.0.0.1.32.64.64.15.1.1.2.50.0.0.0.2.0.0.1'
                ],
            ],
            {
                "0": FjdaryeRlun(
                    rlun_index="0",
                    raw_string="\x00\x00\x00\xa0\x10\x10\x00\x00\x03\x00\x00\x00\x00ÿÿÿ\x00\x00@Í\x04\x00\x00\x00\x00\x06\x00\x00\x00\x06\x00\x00\x00\x00\x00\x00\x01 @@\x0f\x01\x01\x022\x00\x00\x00\x02\x00\x00\x01",
                )
            },
            id="Transforms the raw input into a mapping containing the index of the rlun and raw ip",
        ),
    ],
)
def test_parse_fjdarye_rluns(
    section: StringTable,
    parse_result: Mapping[str, FjdaryeRlun],
) -> None:
    assert parse_fjdarye_rluns(section) == parse_result


@pytest.mark.parametrize(
    "section, discovery_result",
    [
        pytest.param(
            {
                "0": FjdaryeRlun(
                    rlun_index="0",
                    raw_string="\x00\x00\x00\xa0\x10\x10\x00\x00\x03\x00\x00\x00\x00ÿÿÿ\x00\x00@Í\x04\x00\x00\x00\x00\x06\x00\x00\x00\x06\x00\x00\x00\x00\x00\x00\x01 @@\x0f\x01\x01\x022\x00\x00\x00\x02\x00\x00\x01",
                )
            },
            [("0", {})],
            id="Because the value of the fourth byte is '\xa0'(160) RLUN is present and a service is discovered. The item name is the index of the RLUN.",
        ),
        pytest.param(
            {
                "0": FjdaryeRlun(
                    rlun_index="0",
                    raw_string="\x00\x00\x00\x33\x10\x10\x00\x00\x03\x00\x00\x00\x00ÿÿÿ\x00\x00@Í\x04\x00\x00\x00\x00\x06\x00\x00\x00\x06\x00\x00\x00\x00\x00\x00\x01 @@\x0f\x01\x01\x022\x00\x00\x00\x02\x00\x00\x01",
                )
            },
            [],
            id="RLUN is not present and no service is discovered, because the value of the fourth byte is not '\xa0'(160)",
        ),
    ],
)
def test_discover_fjdarye_rluns(
    section: Mapping[str, FjdaryeRlun],
    discovery_result: Sequence[tuple[str, str, None]],
) -> None:
    assert list(discover_fjdarye_rluns(section)) == discovery_result


@pytest.mark.parametrize(
    "section, item, rluns_check_result",
    [
        pytest.param(
            {
                "0": FjdaryeRlun(
                    rlun_index="0",
                    raw_string="\x00\x00\x00\xa0\x10\x10\x00\x00\x03\x00\x00\x00\x00ÿÿÿ\x00\x00@Í\x04\x00\x00\x00\x00\x06\x00\x00\x00\x06\x00\x00\x00\x00\x00\x00\x01 @@\x0f\x01\x01\x022\x00\x00\x00\x02\x00\x00\x01",
                )
            },
            "2",
            [],
            id="If the item is not in the section, the check result is None",
        ),
        pytest.param(
            {
                "0": FjdaryeRlun(
                    rlun_index="0",
                    raw_string="\x00\x00\x00\x43\x10\x10\x00\x00\x03\x00\x00\x00\x00ÿÿÿ\x00\x00@Í\x04\x00\x00\x00\x00\x06\x00\x00\x00\x06\x00\x00\x00\x00\x00\x00\x01 @@\x0f\x01\x01\x022\x00\x00\x00\x02\x00\x00\x01",
                )
            },
            "0",
            [(2, "RLUN is not present")],
            id="If the fourth byte is not equal to '\xa0'(160), RLUN is not present and check result state is CRIT",
        ),
        pytest.param(
            {
                "0": FjdaryeRlun(
                    rlun_index="0",
                    raw_string="\x00\x00\x08\xa0\x10\x10\x00\x00\x03\x00\x00\x00\x00ÿÿÿ\x00\x00@Í\x04\x00\x00\x00\x00\x06\x00\x00\x00\x06\x00\x00\x00\x00\x00\x00\x01 @@\x0f\x01\x01\x022\x00\x00\x00\x02\x00\x00\x01",
                )
            },
            "0",
            [(1, "RLUN is rebuilding")],
            id="If the third byte is equal to '\x08'(8), RLUN is rebuilding and result state is WARN",
        ),
        pytest.param(
            {
                "0": FjdaryeRlun(
                    rlun_index="0",
                    raw_string="\x00\x00\x07\xa0\x10\x10\x00\x00\x03\x00\x00\x00\x00ÿÿÿ\x00\x00@Í\x04\x00\x00\x00\x00\x06\x00\x00\x00\x06\x00\x00\x00\x00\x00\x00\x01 @@\x0f\x01\x01\x022\x00\x00\x00\x02\x00\x00\x01",
                )
            },
            "0",
            [(1, "RLUN copyback in progress")],
            id="If the third byte is equal to '\x07'(7), RLUN copyback is in progress and result state is WARN",
        ),
        pytest.param(
            {
                "0": FjdaryeRlun(
                    rlun_index="0",
                    raw_string="\x00\x00\x41\xa0\x10\x10\x00\x00\x03\x00\x00\x00\x00ÿÿÿ\x00\x00@Í\x04\x00\x00\x00\x00\x06\x00\x00\x00\x06\x00\x00\x00\x00\x00\x00\x01 @@\x0f\x01\x01\x022\x00\x00\x00\x02\x00\x00\x01",
                )
            },
            "0",
            [(1, "RLUN spare is in use")],
            id="If the third byte is equal to '\x41'(65), RLUN spare is in use and result state is WARN",
        ),
        pytest.param(
            {
                "0": FjdaryeRlun(
                    rlun_index="0",
                    raw_string="\x00\x00\x42\xa0\x10\x10\x00\x00\x03\x00\x00\x00\x00ÿÿÿ\x00\x00@Í\x04\x00\x00\x00\x00\x06\x00\x00\x00\x06\x00\x00\x00\x00\x00\x00\x01 @@\x0f\x01\x01\x022\x00\x00\x00\x02\x00\x00\x01",
                )
            },
            "0",
            [(0, "RLUN is in RAID0 state")],
            id="If the third byte is equal to '\x42'(66), RLUN is in RAID0 state and result state is OK",
        ),
        pytest.param(
            {
                "0": FjdaryeRlun(
                    rlun_index="0",
                    raw_string="\x00\x00\x00\xa0\x10\x10\x00\x00\x03\x00\x00\x00\x00ÿÿÿ\x00\x00@Í\x04\x00\x00\x00\x00\x06\x00\x00\x00\x06\x00\x00\x00\x00\x00\x00\x01 @@\x0f\x01\x01\x022\x00\x00\x00\x02\x00\x00\x01",
                )
            },
            "0",
            [(0, "RLUN is in normal state")],
            id="If the third byte is equal to '\x00'(0), RLUN is in normal state and result state is OK",
        ),
        pytest.param(
            {
                "0": FjdaryeRlun(
                    rlun_index="0",
                    raw_string="\x00\x00\x44\xa0\x10\x10\x00\x00\x03\x00\x00\x00\x00ÿÿÿ\x00\x00@Í\x04\x00\x00\x00\x00\x06\x00\x00\x00\x06\x00\x00\x00\x00\x00\x00\x01 @@\x0f\x01\x01\x022\x00\x00\x00\x02\x00\x00\x01",
                )
            },
            "0",
            [(2, "RLUN in unknown state")],
            id="If RLUN is present and none of the above criteria are met, the RLUN state is uknown and the result state is CRIT",
        ),
    ],
)
def test_check_fjdarye_rluns(
    section: Mapping[str, FjdaryeRlun],
    item: str,
    rluns_check_result: FjdaryeCheckResult,
) -> None:
    assert list(check_fjdarye_rluns(item, {}, section)) == rluns_check_result


@pytest.mark.parametrize(
    "section, parse_sum_result",
    [
        pytest.param(
            [["3"]],
            FjdaryeDeviceStatus("3"),
            id="If the length of the input section is 1, a Mapping containing the status is parsed.",
        ),
        pytest.param(
            [["3", "4"]],
            None,
            id="If the length of the input section is more than 1, nothing in parsed",
        ),
        pytest.param(
            [],
            None,
            id="If the length of the input section is 0, nothing is parsed",
        ),
    ],
)
def test_parse_fjdarye_sum(
    section: StringTable,
    parse_sum_result: Optional[FjdaryeDeviceStatus],
) -> None:
    assert parse_fjdarye_sum(section) == parse_sum_result


@pytest.mark.parametrize(
    "section, discovery_result",
    [
        # Assumption: The input will always be a FjdaryeDeviceStatus, because it's the output of the parse_fjdarye_sum function,
        pytest.param(
            FjdaryeDeviceStatus("3"),
            [("0", {})],
            id="If the length of the input section is 1, a service with name '0' is discovered",
        ),
        pytest.param(
            None,
            [],
            id="If the length of the input section is not 1, no services are discovered",
        ),
    ],
)
def test_discover_fjdarye_sum(
    section: Optional[FjdaryeDeviceStatus],
    discovery_result: Sequence[tuple[str, Mapping]],
) -> None:
    assert list(discover_fjdarye_sum(section)) == discovery_result


@pytest.mark.parametrize(
    "section, check_sum_result",
    [
        pytest.param(
            None,
            [],
            id="If the input is None, the check result is an empty list, which leads to the state going to UNKNOWN",
        ),
        pytest.param(
            FjdaryeDeviceStatus("3"),
            [(0, "Status: ok")],
            id="If the summary status is equal to 3, the check result state is OK",
        ),
        pytest.param(
            FjdaryeDeviceStatus("4"),
            [(1, "Status: warning")],
            id="If the summary status is equal 4, the check result state is WARN",
        ),
        pytest.param(
            FjdaryeDeviceStatus("5"),
            [(2, "Status: failed")],
            id="If the summary status is 1 or 2 or 5, the check result state is WARN and the description is the corresponding value from the fjdarye_sum_status mapping",
        ),
        pytest.param(
            FjdaryeDeviceStatus("6"),
            [(3, "Status: unknown")],
            id="If the summary status not known, the check result is UNKNOWN.",
        ),
    ],
)
def test_check_fjdarye_sum(
    section: Optional[FjdaryeDeviceStatus],
    check_sum_result: Sequence[tuple[int, str]],
) -> None:
    assert list(check_fjdarye_sum(_item="", _no_param={}, section=section)) == check_sum_result
