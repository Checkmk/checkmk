#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from typing import Any

from cmk.agent_based.v2 import Metric, Result, State, StringTable
from cmk.plugins.redfish.agent_based.redfish_powersubsystem import (
    check_redfish_powersubsystem,
    discovery_redfish_powersubsystem,
)
from cmk.plugins.redfish.lib import parse_redfish_multiple


def _make_powersubsystem(
    subsystem_id: str = "PowerSubsystem",
    *,
    capacity_watts: float = 1960.0,
    allocated_watts: float = 1518.0,
    redundancy_type: str = "NPlusM",
    redundancy_health: str = "OK",
    redundancy_state: str = "Enabled",
    num_psus: int = 2,
    min_needed: int = 1,
    health: str = "OK",
    state: str = "Enabled",
) -> dict[str, Any]:
    return {
        "@odata.id": "/redfish/v1/Chassis/System.Embedded.1/PowerSubsystem",
        "@odata.type": "#PowerSubsystem.v1_1_0.PowerSubsystem",
        "Id": subsystem_id,
        "CapacityWatts": capacity_watts,
        "Allocation": {"AllocatedWatts": allocated_watts},
        "PowerSupplyRedundancy": [
            {
                "RedundancyType": redundancy_type,
                "MinNeededInGroup": min_needed,
                "MaxSupportedInGroup": num_psus,
                "RedundancyGroup": [
                    {"@odata.id": f"/redfish/v1/.../PSU.Slot.{i + 1}"} for i in range(num_psus)
                ],
                "Status": {"Health": redundancy_health, "State": redundancy_state},
            }
        ],
        "Status": {"Health": health, "State": state},
    }


def _make_string_table(*entries: dict[str, Any]) -> StringTable:
    return [[json.dumps(e)] for e in entries]


def test_discovery() -> None:
    parsed = parse_redfish_multiple(_make_string_table(_make_powersubsystem()))
    services = list(discovery_redfish_powersubsystem(parsed))
    assert len(services) == 1


def test_check_ok() -> None:
    parsed = parse_redfish_multiple(_make_string_table(_make_powersubsystem()))
    item = next(iter(parsed))
    results = list(check_redfish_powersubsystem(item, parsed))

    result_items = [r for r in results if isinstance(r, Result)]
    metric_items = [r for r in results if isinstance(r, Metric)]

    assert any("Normal" in r.summary for r in result_items if r.summary)
    assert any("Redundancy: NPlusM" in r.summary for r in result_items if r.summary)
    assert any(m.name == "power_capacity" and m.value == 1960.0 for m in metric_items)


def test_check_degraded_redundancy() -> None:
    parsed = parse_redfish_multiple(
        _make_string_table(_make_powersubsystem(redundancy_health="Critical", num_psus=1))
    )
    item = next(iter(parsed))
    results = list(check_redfish_powersubsystem(item, parsed))

    result_items = [r for r in results if isinstance(r, Result)]
    assert any(r.state == State.CRIT for r in result_items)


def test_check_missing_item() -> None:
    parsed = parse_redfish_multiple(_make_string_table(_make_powersubsystem()))
    results = list(check_redfish_powersubsystem("nonexistent", parsed))
    assert len(results) == 0
