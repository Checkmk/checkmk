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
    manufacturer: str = "DELL",
    model: str = "PWR SPLY,1400W,RDNT,LTON",
    firmware: str = "00.18.31",
    capacity_watts: float = 1400.0,
    line_input_status: str = "Normal",
    health: str = "OK",
    state: str = "Enabled",
) -> dict[str, Any]:
    return {
        "@odata.id": f"/redfish/v1/Chassis/System/PowerSubsystem/PowerSupplies/{psu_id}",
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


def _item_for(psu_id: str) -> str:
    return f"/redfish/v1/Chassis/System/PowerSubsystem/PowerSupplies/{psu_id}"


def test_discovery() -> None:
    parsed = parse_redfish_multiple(_make_string_table(_make_powersupply()))
    services = list(discovery_redfish_powersupplies(parsed))
    assert len(services) == 1
    assert services[0].item == _item_for("PSU.Slot.1")


def test_discovery_skips_absent() -> None:
    parsed = parse_redfish_multiple(_make_string_table(_make_powersupply(state="Absent")))
    services = list(discovery_redfish_powersupplies(parsed))
    assert len(services) == 0


def test_discovery_two_psus() -> None:
    parsed = parse_redfish_multiple(
        _make_string_table(
            _make_powersupply("PSU.Slot.1"),
            _make_powersupply("PSU.Slot.2"),
        )
    )
    items = {s.item for s in discovery_redfish_powersupplies(parsed)}
    assert items == {_item_for("PSU.Slot.1"), _item_for("PSU.Slot.2")}


def test_check_ok() -> None:
    parsed = parse_redfish_multiple(_make_string_table(_make_powersupply()))
    results = list(check_redfish_powersupplies(_item_for("PSU.Slot.1"), parsed))

    result_items = [r for r in results if isinstance(r, Result)]
    metric_items = [r for r in results if isinstance(r, Metric)]

    assert any("DELL" in r.summary for r in result_items if r.summary)
    assert any("1400 W" in r.summary for r in result_items if r.summary)
    assert any("Normal" in r.summary for r in result_items if r.summary)
    assert any(m.name == "power_capacity" and m.value == 1400.0 for m in metric_items)


def test_check_critical() -> None:
    parsed = parse_redfish_multiple(_make_string_table(_make_powersupply(health="Critical")))
    results = list(check_redfish_powersupplies(_item_for("PSU.Slot.1"), parsed))
    result_items = [r for r in results if isinstance(r, Result)]
    assert any(r.state == State.CRIT for r in result_items)


def test_check_missing_item() -> None:
    parsed = parse_redfish_multiple(_make_string_table(_make_powersupply()))
    results = list(check_redfish_powersupplies("nonexistent", parsed))
    assert len(results) == 0
