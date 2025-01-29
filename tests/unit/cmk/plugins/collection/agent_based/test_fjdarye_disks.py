#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from cmk.agent_based.v2 import CheckResult, DiscoveryResult, Result, Service, State, StringTable
from cmk.plugins.collection.agent_based.fjdarye_disks import (
    check_fjdarye_disks,
    check_fjdarye_disks_summary,
    discover_fjdarye_disks,
    discover_fjdarye_disks_summary,
    FjdaryeDisk,
    parse_fjdarye_disks,
    SectionFjdaryeDisk,
)


@pytest.mark.parametrize(
    # Assumption: The fjdarye_disks_status mapping consistantly gives us a tuple of (state, state_description)
    # Assumption: Section will always be a StringTable
    "section, parse_result",
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
                "0": FjdaryeDisk(
                    disk_index="0", state=State.OK, state_description="available", state_disk="1"
                ),
                "1": FjdaryeDisk(
                    disk_index="1", state=State.OK, state_description="available", state_disk="1"
                ),
                "2": FjdaryeDisk(
                    disk_index="2", state=State.OK, state_description="available", state_disk="1"
                ),
                "3": FjdaryeDisk(
                    disk_index="3", state=State.OK, state_description="available", state_disk="1"
                ),
                "4": FjdaryeDisk(
                    disk_index="4",
                    state=State.WARN,
                    state_description="notsupported",
                    state_disk="4",
                ),
            },
            id="Returns disk information based on the disk_state attribute",
        ),
        pytest.param(
            [
                [
                    ["0", "1"],
                    ["4", "4"],
                    ["14", "14"],
                ],
                [],
                [],
            ],
            {
                "0": FjdaryeDisk(
                    disk_index="0", state=State.OK, state_description="available", state_disk="1"
                ),
                "4": FjdaryeDisk(
                    disk_index="4",
                    state=State.WARN,
                    state_description="notsupported",
                    state_disk="4",
                ),
                "14": FjdaryeDisk(
                    disk_index="14",
                    state=State.UNKNOWN,
                    state_description="unknown[14]",
                    state_disk="14",
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
                [
                    ["0", "1"],
                    ["4", "4"],
                    ["14", "14"],
                    ["14", "1"],
                ],
                [],
                [],
            ],
            {
                "0": FjdaryeDisk(
                    disk_index="0", state=State.OK, state_description="available", state_disk="1"
                ),
                "4": FjdaryeDisk(
                    disk_index="4",
                    state=State.WARN,
                    state_description="notsupported",
                    state_disk="4",
                ),
                "14": FjdaryeDisk(
                    disk_index="14",
                    state=State.UNKNOWN,
                    state_description="unknown[14]",
                    state_disk="14",
                ),
            },
            id="If the parse function is trying to alter already existing elements in the parsed section it should not allow it and should keep the existing state",
        ),
    ],
)
def test_parse_fjdarye_disks(
    section: Sequence[StringTable],
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
                [
                    ["0", "1", "3"],
                    ["1", "1"],
                    ["2", "1"],
                    ["3", "1"],
                    ["4", "4"],
                ],
                [],
                [],
            ],
            id="If info contains more than 2 elements, the parse function should raise a ValueError",
        ),
        pytest.param(
            [
                [
                    ["0"],
                    ["1", "1"],
                    ["2", "1"],
                    ["3", "1"],
                    ["4", "4"],
                ],
                [],
                [],
            ],
            id="If info contains less than 2 elements, the parse function should raise a ValueError",
        ),
    ],
)
def test_parse_fjdarye_disks_with_error_input(
    section: Sequence[StringTable],
) -> None:
    with pytest.raises(ValueError):
        assert parse_fjdarye_disks(section)


@pytest.mark.parametrize(
    # Assumption: The input parameter type will be correct, because it's the output of a previously tested function
    "section, discovery_result",
    [
        pytest.param(
            {
                "0": FjdaryeDisk(
                    disk_index="0", state=State.OK, state_description="available", state_disk="1"
                ),
                "1": FjdaryeDisk(
                    disk_index="1", state=State.OK, state_description="available", state_disk="1"
                ),
                "2": FjdaryeDisk(
                    disk_index="2", state=State.OK, state_description="available", state_disk="1"
                ),
                "3": FjdaryeDisk(
                    disk_index="3", state=State.OK, state_description="available", state_disk="1"
                ),
                "4": FjdaryeDisk(
                    disk_index="4",
                    state=State.WARN,
                    state_description="notsupported",
                    state_disk="3",
                ),
            },
            [
                Service(item="0", parameters={"expected_state": "available"}),
                Service(item="1", parameters={"expected_state": "available"}),
                Service(item="2", parameters={"expected_state": "available"}),
                Service(item="3", parameters={"expected_state": "available"}),
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
    section: SectionFjdaryeDisk,
    discovery_result: DiscoveryResult,
) -> None:
    assert list(discover_fjdarye_disks(section)) == discovery_result


@pytest.mark.parametrize(
    "section, item, params, check_result",
    [
        pytest.param(
            {
                "0": FjdaryeDisk(
                    disk_index="0", state=State.OK, state_description="available", state_disk="1"
                ),
                "1": FjdaryeDisk(
                    disk_index="1", state=State.OK, state_description="available", state_disk="1"
                ),
                "2": FjdaryeDisk(
                    disk_index="2", state=State.OK, state_description="available", state_disk="1"
                ),
                "3": FjdaryeDisk(
                    disk_index="3", state=State.OK, state_description="available", state_disk="1"
                ),
                "4": FjdaryeDisk(
                    disk_index="4",
                    state=State.WARN,
                    state_description="notavailable",
                    state_disk="3",
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
                    disk_index="0", state=State.OK, state_description="available", state_disk="1"
                ),
                "1": FjdaryeDisk(
                    disk_index="1", state=State.OK, state_description="available", state_disk="1"
                ),
                "2": FjdaryeDisk(
                    disk_index="2", state=State.OK, state_description="available", state_disk="1"
                ),
                "3": FjdaryeDisk(
                    disk_index="3", state=State.OK, state_description="available", state_disk="1"
                ),
                "4": FjdaryeDisk(
                    disk_index="4",
                    state=State.WARN,
                    state_description="notavailable",
                    state_disk="3",
                ),
            },
            "3",
            {"expected_state": "available"},
            [Result(state=State.OK, summary="Status: available")],
            id="If no rules are configured, the expected_state of the disk is its state_description at the time it was discovered.",
        ),
        pytest.param(
            {
                "0": FjdaryeDisk(
                    disk_index="0", state=State.OK, state_description="available", state_disk="1"
                ),
                "1": FjdaryeDisk(
                    disk_index="1", state=State.OK, state_description="available", state_disk="1"
                ),
                "2": FjdaryeDisk(
                    disk_index="2", state=State.OK, state_description="available", state_disk="1"
                ),
                "3": FjdaryeDisk(
                    disk_index="3", state=State.OK, state_description="available", state_disk="1"
                ),
                "4": FjdaryeDisk(
                    disk_index="4",
                    state=State.WARN,
                    state_description="notavailable",
                    state_disk="3",
                ),
            },
            "4",
            {},
            [Result(state=State.OK, summary="Status: notavailable")],
            id="If a rule with no parameters is created, the state is OK and the summary is the device's status description.",
        ),
        pytest.param(
            {
                "0": FjdaryeDisk(
                    disk_index="0", state=State.OK, state_description="available", state_disk="1"
                ),
                "1": FjdaryeDisk(
                    disk_index="1", state=State.OK, state_description="available", state_disk="1"
                ),
                "2": FjdaryeDisk(
                    disk_index="2", state=State.OK, state_description="available", state_disk="1"
                ),
                "3": FjdaryeDisk(
                    disk_index="3", state=State.OK, state_description="available", state_disk="1"
                ),
                "4": FjdaryeDisk(
                    disk_index="4",
                    state=State.WARN,
                    state_description="notavailable",
                    state_disk="3",
                ),
            },
            "4",
            {"expected_state": "available"},
            [Result(state=State.CRIT, summary="Status: notavailable (expected: available)")],
            id="If only the expected_state parameter is configured in the ruleset and it doesn't match the current state of the disk, the result is a state of CRIT with a description indicating the difference between states.",
        ),
        pytest.param(
            {
                "0": FjdaryeDisk(
                    disk_index="0", state=State.OK, state_description="available", state_disk="1"
                ),
                "1": FjdaryeDisk(
                    disk_index="1", state=State.OK, state_description="available", state_disk="1"
                ),
                "2": FjdaryeDisk(
                    disk_index="2", state=State.OK, state_description="available", state_disk="1"
                ),
                "3": FjdaryeDisk(
                    disk_index="3", state=State.OK, state_description="available", state_disk="1"
                ),
                "4": FjdaryeDisk(
                    disk_index="4",
                    state=State.WARN,
                    state_description="notavailable",
                    state_disk="3",
                ),
            },
            "3",
            {"expected_state": "available"},
            [Result(state=State.OK, summary="Status: available")],
            id="If only the expected_state parameter is configured in the ruleset and it matches the current state of the disk, the result is a state of OK with a summary indicating the state of the disk.",
        ),
        pytest.param(
            {
                "0": FjdaryeDisk(
                    disk_index="0", state=State.OK, state_description="available", state_disk="1"
                ),
                "1": FjdaryeDisk(
                    disk_index="1", state=State.OK, state_description="available", state_disk="1"
                ),
                "2": FjdaryeDisk(
                    disk_index="2", state=State.OK, state_description="available", state_disk="1"
                ),
                "3": FjdaryeDisk(
                    disk_index="3", state=State.OK, state_description="available", state_disk="1"
                ),
                "4": FjdaryeDisk(
                    disk_index="4",
                    state=State.WARN,
                    state_description="notavailable",
                    state_disk="3",
                ),
            },
            "4",
            {"use_device_states": True},
            [Result(state=State.WARN, summary="Status: notavailable (using device states)")],
            id="If the use_device_states parameter is configures to True in the ruleset, the function uses the current device state as the result. It also provides a note in the result that it's using it.",
        ),
        pytest.param(
            {
                "0": FjdaryeDisk(
                    disk_index="0", state=State.OK, state_description="available", state_disk="1"
                ),
                "1": FjdaryeDisk(
                    disk_index="1", state=State.OK, state_description="available", state_disk="1"
                ),
                "2": FjdaryeDisk(
                    disk_index="2", state=State.OK, state_description="available", state_disk="1"
                ),
                "3": FjdaryeDisk(
                    disk_index="3", state=State.OK, state_description="available", state_disk="1"
                ),
                "4": FjdaryeDisk(
                    disk_index="4",
                    state=State.WARN,
                    state_description="notavailable",
                    state_disk="3",
                ),
            },
            "4",
            {"use_device_states": False},
            [Result(state=State.OK, summary="Status: notavailable")],
            id="If the use_device_states parameter is configures to False in the ruleset, the expected_state of the disk is its state_description at the time it was discovered. Basically, the behaviour is the same as if the parameter use_device_state wasn't even configured.",
        ),
        pytest.param(
            {
                "0": FjdaryeDisk(
                    disk_index="0", state=State.OK, state_description="available", state_disk="1"
                ),
                "1": FjdaryeDisk(
                    disk_index="1", state=State.OK, state_description="available", state_disk="1"
                ),
                "2": FjdaryeDisk(
                    disk_index="2", state=State.OK, state_description="available", state_disk="1"
                ),
                "3": FjdaryeDisk(
                    disk_index="3", state=State.OK, state_description="available", state_disk="1"
                ),
                "4": FjdaryeDisk(
                    disk_index="4",
                    state=State.WARN,
                    state_description="notavailable",
                    state_disk="3",
                ),
            },
            "4",
            {"expected_state": "available", "use_device_states": True},
            [Result(state=State.WARN, summary="Status: notavailable (using device states)")],
            id="If both the use_device_states and expected_state are configured in the ruleset, the function uses the current device state as the result. Same behaviour as if the expected_state parameter was not configured.",
        ),
        pytest.param(
            {
                "0": FjdaryeDisk(
                    disk_index="0", state=State.OK, state_description="available", state_disk="1"
                ),
                "1": FjdaryeDisk(
                    disk_index="1", state=State.OK, state_description="available", state_disk="1"
                ),
                "2": FjdaryeDisk(
                    disk_index="2", state=State.OK, state_description="available", state_disk="1"
                ),
                "3": FjdaryeDisk(
                    disk_index="3", state=State.OK, state_description="available", state_disk="1"
                ),
                "4": FjdaryeDisk(
                    disk_index="4",
                    state=State.WARN,
                    state_description="notavailable",
                    state_disk="3",
                ),
            },
            "4",
            {"expected_state": "available", "use_device_states": False},
            [Result(state=State.CRIT, summary="Status: notavailable (expected: available)")],
            id="If use_device_states is configured to False and expected_state is configured in the ruleset, the behaviour is as if only the expected_state was configured.",
        ),
    ],
)
def test_check_fjdarye_disks(
    section: SectionFjdaryeDisk,
    item: str,
    params: Mapping[str, Any],
    check_result: CheckResult,
) -> None:
    assert list(check_fjdarye_disks(item, params, section)) == check_result


# fjdarye_disks_summary ###########


@pytest.mark.parametrize(
    "section, discovery_summary_result",
    [
        pytest.param(
            {},
            [],
            id="If the section is empty, no items are discovered",
        ),
        pytest.param(
            {
                "0": FjdaryeDisk(
                    disk_index="0", state=State.OK, state_description="available", state_disk="1"
                ),
                "1": FjdaryeDisk(
                    disk_index="1", state=State.OK, state_description="available", state_disk="1"
                ),
                "2": FjdaryeDisk(
                    disk_index="2", state=State.OK, state_description="available", state_disk="1"
                ),
                "3": FjdaryeDisk(
                    disk_index="3", state=State.OK, state_description="available", state_disk="1"
                ),
                "4": FjdaryeDisk(
                    disk_index="4",
                    state=State.WARN,
                    state_description="notavailable",
                    state_disk="3",
                ),
            },
            [Service(parameters={"available": 4})],
            id="Discovers a service without item and discovery parameters, which indicates the current device states.",
        ),
        pytest.param(
            {
                "0": FjdaryeDisk(
                    disk_index="0", state=State.OK, state_description="available", state_disk="1"
                ),
                "1": FjdaryeDisk(
                    disk_index="1", state=State.OK, state_description="available", state_disk="1"
                ),
                "4": FjdaryeDisk(
                    disk_index="4",
                    state=State.WARN,
                    state_description="notavailable",
                    state_disk="3",
                ),
            },
            [Service(parameters={"available": 2})],
            id="Discovers a service without item and discovery parameters, which indicates the current device states. The summary does not include disks with state_disk=3",
        ),
    ],
)
def test_discover_fjdarye_disks_summary(
    section: SectionFjdaryeDisk,
    discovery_summary_result: DiscoveryResult,
) -> None:
    assert list(discover_fjdarye_disks_summary(section)) == discovery_summary_result


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
                    disk_index="0", state=State.OK, state_description="available", state_disk="1"
                ),
                "3": FjdaryeDisk(
                    disk_index="1", state=State.CRIT, state_description="broken", state_disk="2"
                ),
                "4": FjdaryeDisk(
                    disk_index="4",
                    state=State.WARN,
                    state_description="notsupported",
                    state_disk="4",
                ),
            },
            {"available": 1, "broken": 1, "notsupported": 1},
            [Result(state=State.OK, summary="Available: 1, Broken: 1, Notsupported: 1")],
            id="If the number of disks in a specific state is equal to the expected number and use_device_state is not configured, the check result state is OK",
        ),
        pytest.param(
            {
                "0": FjdaryeDisk(
                    disk_index="0", state=State.OK, state_description="available", state_disk="1"
                ),
                "3": FjdaryeDisk(
                    disk_index="1", state=State.CRIT, state_description="broken", state_disk="2"
                ),
                "4": FjdaryeDisk(
                    disk_index="4",
                    state=State.WARN,
                    state_description="notsupported",
                    state_disk="4",
                ),
            },
            {"available": 2, "broken": 1, "notsupported": 1, "use_device_states": False},
            [
                Result(
                    state=State.CRIT,
                    summary="Available: 1, Broken: 1, Notsupported: 1 (expected: Available: 2, Broken: 1, Notsupported: 1)",
                )
            ],
            id="If the number of disks in a specific state is lower than the expected number and use_device_state is not configured, the check result is CRIT",
        ),
        pytest.param(
            {
                "0": FjdaryeDisk(
                    disk_index="0", state=State.OK, state_description="available", state_disk="1"
                ),
                "1": FjdaryeDisk(
                    disk_index="1", state=State.OK, state_description="available", state_disk="1"
                ),
                "3": FjdaryeDisk(
                    disk_index="1", state=State.CRIT, state_description="broken", state_disk="2"
                ),
                "4": FjdaryeDisk(
                    disk_index="4",
                    state=State.WARN,
                    state_description="notsupported",
                    state_disk="4",
                ),
            },
            {"available": 1, "broken": 1, "notsupported": 1, "use_device_states": False},
            [
                Result(
                    state=State.WARN,
                    summary="Available: 2, Broken: 1, Notsupported: 1 (expected: Available: 1, Broken: 1, Notsupported: 1)",
                )
            ],
            id="If the number of disks in a specific state is higher than the expected number and use_device_state is not configured, the check result is WARN",
        ),
        pytest.param(
            # Because the State.worst() function is used, State.CRIT is considered worse than State.UNKNOWN
            # OK < WARN < UNKNOWN < CRIT
            {
                "0": FjdaryeDisk(
                    disk_index="0", state=State.OK, state_description="available", state_disk="1"
                ),
                "3": FjdaryeDisk(
                    disk_index="1", state=State.CRIT, state_description="broken", state_disk="2"
                ),
                "4": FjdaryeDisk(
                    disk_index="4",
                    state=State.WARN,
                    state_description="notsupported",
                    state_disk="4",
                ),
                "14": FjdaryeDisk(
                    disk_index="14",
                    state=State.UNKNOWN,
                    state_description="unknown[14]",
                    state_disk="14",
                ),
            },
            {
                "use_device_states": True,
            },
            [
                Result(
                    state=State.CRIT,
                    summary="Available: 1, Broken: 1, Notsupported: 1, Unknown[14]: 1 (using device states)",
                )
            ],
            id="If use_device_states is set to True, the check result state is the max mapped value from the map_states mapping (worst state of the selected disks).",
        ),
    ],
)
def test_check_fjdarye_disks_summary(
    section: SectionFjdaryeDisk,
    params: Mapping[str, int | bool],
    check_result: CheckResult,
) -> None:
    assert list(check_fjdarye_disks_summary(params=params, section=section)) == check_result
