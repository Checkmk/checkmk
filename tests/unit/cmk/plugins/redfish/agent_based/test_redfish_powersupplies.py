#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from typing import Any

from cmk.agent_based.v2 import Metric, Result, State, StringTable
from cmk.plugins.redfish.agent_based.redfish_powersupplies import (
    check_redfish_powersupplies,
    discovery_redfish_powersupplies,
)
from cmk.plugins.redfish.lib import parse_redfish_multiple


def _make_powersupply(
    psu_id: str = "PSU.Slot.1",
    *,
    chassis: str = "System",
    manufacturer: str = "DELL",
    model: str = "PWR SPLY,1400W,RDNT,LTON",
    firmware: str = "00.18.31",
    capacity_watts: float = 1400.0,
    line_input_status: str = "Normal",
    health: str = "OK",
    state: str = "Enabled",
) -> dict[str, Any]:
    return {
        "@odata.id": f"/redfish/v1/Chassis/{chassis}/PowerSubsystem/PowerSupplies/{psu_id}",
        "@odata.type": "#PowerSupply.v1_5_1.PowerSupply",
        "Id": psu_id,
        "Manufacturer": manufacturer,
        "Model": model,
        "FirmwareVersion": firmware,
        "InputRanges": [{"CapacityWatts": capacity_watts, "NominalVoltageType": "AC100To240V"}],
        "LineInputStatus": line_input_status,
        "Status": {"Health": health, "State": state},
    }


def _make_string_table(*entries: dict[str, Any]) -> StringTable:
    return [[json.dumps(e)] for e in entries]


def test_discovery() -> None:
    parsed = parse_redfish_multiple(_make_string_table(_make_powersupply()))
    services = list(discovery_redfish_powersupplies(parsed))
    assert len(services) == 1
    assert services[0].item == "System/PSU.Slot.1"


def test_discovery_skips_absent() -> None:
    parsed = parse_redfish_multiple(_make_string_table(_make_powersupply(state="Absent")))
    services = list(discovery_redfish_powersupplies(parsed))
    assert len(services) == 0


def test_discovery_two_psus_same_chassis() -> None:
    parsed = parse_redfish_multiple(
        _make_string_table(
            _make_powersupply("PSU.Slot.1"),
            _make_powersupply("PSU.Slot.2"),
        )
    )
    items = {s.item for s in discovery_redfish_powersupplies(parsed)}
    assert items == {"System/PSU.Slot.1", "System/PSU.Slot.2"}


def test_discovery_same_psu_id_on_two_chassis_does_not_collide() -> None:
    """Regression: two chassis reporting PSU.Slot.1 must each yield a service.

    Previously the entry was keyed by Id alone, so the second chassis' PSU
    silently overwrote the first via parsed.setdefault(). The chassis id is
    now part of the item, keeping both distinct.
    """
    parsed = parse_redfish_multiple(
        _make_string_table(
            _make_powersupply("PSU.Slot.1", chassis="Enclosure.1"),
            _make_powersupply("PSU.Slot.1", chassis="Enclosure.2"),
        )
    )
    items = {s.item for s in discovery_redfish_powersupplies(parsed)}
    assert items == {"Enclosure.1/PSU.Slot.1", "Enclosure.2/PSU.Slot.1"}


def test_check_ok() -> None:
    parsed = parse_redfish_multiple(_make_string_table(_make_powersupply()))
    results = list(check_redfish_powersupplies("System/PSU.Slot.1", parsed))

    result_items = [r for r in results if isinstance(r, Result)]
    metric_items = [r for r in results if isinstance(r, Metric)]

    assert any("DELL" in r.summary for r in result_items if r.summary)
    assert any("1400 W" in r.summary for r in result_items if r.summary)
    assert any("Normal" in r.summary for r in result_items if r.summary)
    assert any(m.name == "power_capacity" and m.value == 1400.0 for m in metric_items)


def test_check_critical() -> None:
    parsed = parse_redfish_multiple(_make_string_table(_make_powersupply(health="Critical")))
    results = list(check_redfish_powersupplies("System/PSU.Slot.1", parsed))
    result_items = [r for r in results if isinstance(r, Result)]
    assert any(r.state == State.CRIT for r in result_items)


def test_check_missing_item() -> None:
    parsed = parse_redfish_multiple(_make_string_table(_make_powersupply()))
    results = list(check_redfish_powersupplies("nonexistent", parsed))
    assert len(results) == 0
