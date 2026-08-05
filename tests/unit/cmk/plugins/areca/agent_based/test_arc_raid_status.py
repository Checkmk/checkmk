#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

import pytest

from cmk.agent_based.v2 import CheckResult, DiscoveryResult, Result, Service, State, StringTable
from cmk.plugins.areca.agent_based import arc_raid_status

# The agent runs "cli64 rsf info" and strips the header and footer rules, so every line is
# the whitespace split of:  #  Name  Disks TotalCap FreeCap DiskChannels State
STRING_TABLE: StringTable = [
    ["1", "Raid", "Set", "#", "000", "4", "4000.0GB", "0.0GB", "1234", "Normal"],
    ["2", "Raid", "Set", "#", "001", "3", "2250.5GB", "0.0GB", "123", "Rebuilding"],
    ["3", "Raid", "Set", "#", "002", "2", "1000.0GB", "0.0GB", "12", "Degrade"],
]


def test_parse_keeps_the_string_table() -> None:
    assert arc_raid_status.parse_arc_raid_status(STRING_TABLE) == STRING_TABLE


def test_discover_one_service_per_raid_set() -> None:
    """The number of disks is stored at discovery time so a later change can be detected."""
    assert list(arc_raid_status.discover_arc_raid_status(STRING_TABLE)) == [
        Service(item="1", parameters={"n_disks": 4}),
        Service(item="2", parameters={"n_disks": 3}),
        Service(item="3", parameters={"n_disks": 2}),
    ]


def test_discover_without_any_raid_set() -> None:
    assert list(arc_raid_status.discover_arc_raid_status([])) == []


@pytest.mark.parametrize(
    "raid_state,expected_state,expected_summary",
    [
        pytest.param("Normal", State.OK, "Normal", id="normal"),
        pytest.param("Checking", State.OK, "Checking", id="checking_is_not_a_problem"),
        pytest.param("Rebuilding", State.WARN, "Rebuilding", id="rebuilding"),
        pytest.param("Degrade", State.CRIT, "Degrade", id="degrade"),
        pytest.param("Incompleted", State.CRIT, "Incompleted", id="incompleted"),
        pytest.param("something", State.CRIT, "Something", id="unknown_state_is_critical"),
    ],
)
def test_check_maps_the_raid_state(
    raid_state: str, expected_state: State, expected_summary: str
) -> None:
    section: StringTable = [
        ["1", "Raid", "Set", "#", "000", "4", "4000.0GB", "0.0GB", "1234", raid_state]
    ]

    assert list(arc_raid_status.check_arc_raid_status("1", {"n_disks": 4}, section)) == [
        Result(state=expected_state, summary=expected_summary)
    ]


def test_check_reports_a_lost_disk() -> None:
    """A raid set can report Normal while running on fewer disks than it was discovered with,
    so the disk count is compared separately."""
    section: StringTable = [
        ["1", "Raid", "Set", "#", "000", "3", "4000.0GB", "0.0GB", "123", "Normal"]
    ]

    assert list(arc_raid_status.check_arc_raid_status("1", {"n_disks": 4}, section)) == [
        Result(state=State.OK, summary="Normal"),
        Result(state=State.CRIT, summary="Number of disks has changed from 4 to 3"),
    ]


def test_check_reports_an_added_disk() -> None:
    section: StringTable = [
        ["1", "Raid", "Set", "#", "000", "5", "4000.0GB", "0.0GB", "12345", "Normal"]
    ]

    assert list(arc_raid_status.check_arc_raid_status("1", {"n_disks": 4}, section)) == [
        Result(state=State.OK, summary="Normal"),
        Result(state=State.CRIT, summary="Number of disks has changed from 4 to 5"),
    ]


def test_check_only_looks_at_its_own_raid_set() -> None:
    assert list(arc_raid_status.check_arc_raid_status("2", {"n_disks": 3}, STRING_TABLE)) == [
        Result(state=State.WARN, summary="Rebuilding")
    ]


@pytest.mark.parametrize(
    "item,params,section",
    [
        pytest.param("4", {"n_disks": 4}, STRING_TABLE, id="raid_set_vanished"),
        pytest.param("1", {"n_disks": 4}, [], id="empty_section"),
    ],
)
def test_check_of_a_missing_raid_set_stays_silent(
    item: str, params: Mapping[str, object], section: StringTable
) -> None:
    """Reporting nothing leaves the service stale rather than inventing a state for hardware
    the agent no longer lists."""
    assert list(arc_raid_status.check_arc_raid_status(item, params, section)) == []


def test_check_result_types() -> None:
    results: CheckResult = arc_raid_status.check_arc_raid_status("1", {"n_disks": 4}, STRING_TABLE)
    discovered: DiscoveryResult = arc_raid_status.discover_arc_raid_status(STRING_TABLE)

    assert all(isinstance(result, Result) for result in results)
    assert all(isinstance(service, Service) for service in discovered)
