#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json

from cmk.agent_based.v2 import Result, Service, State
from cmk.plugins.veeam.agent_based.veeam_protection_groups import (
    check_veeam_protection_groups,
    CheckParameters,
    DEFAULT_PARAMETERS,
    discovery_veeam_protection_groups,
    parse_veeam_protection_groups,
)

PARAMS = DEFAULT_PARAMETERS


def _group(name: str = "group-1", **overrides: object) -> str:
    group_dict: dict[str, object] = {
        "id": "id-1",
        "name": name,
        "type": "IndividualComputers",
        "description": "Office machines",
        "isDisabled": False,
        "computers": [{"hostName": "pc-1"}, {"hostName": "pc-2"}],
    }
    group_dict.update(overrides)
    return json.dumps(group_dict)


def test_discovery_veeam_protection_groups() -> None:
    section = parse_veeam_protection_groups([[_group("group-1")], [_group("group-2")]])
    assert list(discovery_veeam_protection_groups(section)) == [
        Service(item="group-1"),
        Service(item="group-2"),
    ]


def test_check_veeam_protection_groups_enabled_is_ok() -> None:
    section = parse_veeam_protection_groups([[_group()]])
    results = list(check_veeam_protection_groups("group-1", PARAMS, section))
    assert results[0] == Result(
        state=State.OK,
        summary="Type: Individual computers, Configured computers: 2, State: Enabled",
    )


def test_check_veeam_protection_groups_empty_computers_counts_zero() -> None:
    section = parse_veeam_protection_groups([[_group(type="ManuallyAdded", computers=[])]])
    results = list(check_veeam_protection_groups("group-1", PARAMS, section))
    assert results[0] == Result(
        state=State.OK,
        summary="Type: Manually added, Configured computers: 0, State: Enabled",
    )


def test_check_veeam_protection_groups_type_without_computers_omits_count() -> None:
    group = json.loads(_group(type="ADObjects"))
    del group["computers"]
    section = parse_veeam_protection_groups([[json.dumps(group)]])
    results = list(check_veeam_protection_groups("group-1", PARAMS, section))
    assert results[0] == Result(
        state=State.OK, summary="Type: Active Directory objects, State: Enabled"
    )
    assert (
        Result(
            state=State.OK,
            notice="Configured computers: not listed for this group type",
        )
        in results
    )


def test_check_veeam_protection_groups_unknown_type_shows_raw_value() -> None:
    section = parse_veeam_protection_groups([[_group(type="SomeFutureType")]])
    results = list(check_veeam_protection_groups("group-1", PARAMS, section))
    assert results[0] == Result(
        state=State.OK,
        summary="Type: SomeFutureType, Configured computers: 2, State: Enabled",
    )


def test_check_veeam_protection_groups_disabled_is_ok_by_default() -> None:
    section = parse_veeam_protection_groups([[_group(isDisabled=True)]])
    results = list(check_veeam_protection_groups("group-1", PARAMS, section))
    assert results[0] == Result(
        state=State.OK,
        summary="Type: Individual computers, Configured computers: 2, State: Disabled",
    )


def test_check_veeam_protection_groups_disabled_state_is_configurable() -> None:
    params = CheckParameters(disabled_state=2)
    section = parse_veeam_protection_groups([[_group(isDisabled=True)]])
    results = list(check_veeam_protection_groups("group-1", params, section))
    assert results[0] == Result(
        state=State.CRIT,
        summary="Type: Individual computers, Configured computers: 2, State: Disabled",
    )


def test_check_veeam_protection_groups_details() -> None:
    section = parse_veeam_protection_groups([[_group()]])
    results = list(check_veeam_protection_groups("group-1", PARAMS, section))
    assert Result(state=State.OK, notice="Description: Office machines") in results


def test_check_veeam_protection_groups_empty_description_shows_none() -> None:
    section = parse_veeam_protection_groups([[_group(description="")]])
    results = list(check_veeam_protection_groups("group-1", PARAMS, section))
    assert Result(state=State.OK, notice="Description: none") in results


def test_check_veeam_protection_groups_vanished_item_yields_nothing() -> None:
    section = parse_veeam_protection_groups([[_group("group-1")]])
    assert list(check_veeam_protection_groups("group-2", PARAMS, section)) == []
