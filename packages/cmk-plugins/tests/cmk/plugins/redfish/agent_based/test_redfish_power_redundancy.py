#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from typing import Any

from cmk.agent_based.v2 import Result, State, StringTable
from cmk.plugins.redfish.agent_based.redfish_power_redundancy import (
    check_redfish_power_redundancy,
    discovery_redfish_power_redundancy,
)
from cmk.plugins.redfish.lib import parse_redfish_multiple


def _make_power_with_redundancy(
    *,
    member_id: str = "0",
    name: str = "System Board PS Redundancy",
    mode: str = "N+m",
    min_needed: int = 1,
    max_supported: int = 2,
    psu_count: int = 2,
    health: str = "OK",
    state: str = "Enabled",
) -> str:
    entry: dict[str, Any] = {
        "@odata.id": "/redfish/v1/Chassis/System.Embedded.1/Power",
        "@odata.type": "#Power.v1_7_1.Power",
        "Id": "Power",
        "Redundancy": [
            {
                "MemberId": member_id,
                "Name": name,
                "Mode": mode,
                "MinNumNeeded": min_needed,
                "MaxNumSupported": max_supported,
                "RedundancySet": [
                    {"@odata.id": f"/redfish/v1/.../PowerSupplies/{i}"} for i in range(psu_count)
                ],
                "Status": {"Health": health, "State": state},
            }
        ],
    }
    return json.dumps(entry)


def _make_string_table(*entries: str) -> StringTable:
    return [[e] for e in entries]


def test_discovery_redfish_power_redundancy() -> None:
    parsed = parse_redfish_multiple(_make_string_table(_make_power_with_redundancy()))
    services = list(discovery_redfish_power_redundancy(parsed))
    assert len(services) == 1
    assert services[0].item == "0"


def test_check_power_redundancy_ok() -> None:
    parsed = parse_redfish_multiple(_make_string_table(_make_power_with_redundancy()))
    results = [r for r in check_redfish_power_redundancy("0", parsed) if isinstance(r, Result)]
    assert len(results) == 2
    assert results[0].state == State.OK
    assert results[1] == Result(
        state=State.OK,
        summary="System Board PS Redundancy, Mode: N+m, Min needed: 1, Max supported: 2, PSUs: 2",
    )


def test_check_power_redundancy_warning() -> None:
    parsed = parse_redfish_multiple(
        _make_string_table(_make_power_with_redundancy(health="Warning"))
    )
    results = [r for r in check_redfish_power_redundancy("0", parsed) if isinstance(r, Result)]
    assert results[0].state == State.WARN


def test_check_power_redundancy_item_not_found() -> None:
    parsed = parse_redfish_multiple(_make_string_table(_make_power_with_redundancy()))
    results = list(check_redfish_power_redundancy("99", parsed))
    assert results == []
