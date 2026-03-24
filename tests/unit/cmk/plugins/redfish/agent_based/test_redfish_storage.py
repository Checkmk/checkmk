#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from typing import Any

from cmk.agent_based.v2 import Result, State, StringTable
from cmk.plugins.redfish.agent_based.redfish_storage import (
    check_redfish_storage,
    check_redfish_storage_battery,
    discovery_redfish_storage,
    discovery_redfish_storage_battery,
)
from cmk.plugins.redfish.lib import parse_redfish_multiple


def _make_storage_entry(
    storage_id: str = "RAID.Slot.3-1",
    *,
    model: str = "PERC H745P Adapter",
    raid_types: list[str] | None = None,
    protocols: list[str] | None = None,
    health: str = "OK",
    state: str = "Enabled",
    battery_status: str | None = None,
) -> str:
    entry: dict[str, Any] = {
        "@odata.id": f"/redfish/v1/Systems/System.Embedded.1/Storage/{storage_id}",
        "@odata.type": "#Storage.v1_15_0.Storage",
        "Id": storage_id,
        "Name": "Storage",
        "StorageControllers": [
            {
                "Model": model,
                "SupportedRAIDTypes": raid_types or ["RAID0", "RAID1", "RAID5"],
                "SupportedDeviceProtocols": protocols or ["SAS", "SATA"],
                "Status": {"Health": health, "State": state},
            }
        ],
        "Status": {"Health": health, "State": state},
    }
    if battery_status is not None:
        entry["Oem"] = {
            "Dell": {
                "DellControllerBattery": {
                    "PrimaryStatus": battery_status,
                    "RAIDState": "Ready",
                }
            }
        }
    return json.dumps(entry)


def _make_string_table(*entries: str) -> StringTable:
    return [[e] for e in entries]


def test_discovery_redfish_storage() -> None:
    parsed = parse_redfish_multiple(_make_string_table(_make_storage_entry()))
    services = list(discovery_redfish_storage(parsed))
    assert len(services) == 1
    assert services[0].item == "RAID.Slot.3-1"


def test_discovery_skips_offline() -> None:
    parsed = parse_redfish_multiple(
        _make_string_table(_make_storage_entry(state="UnavailableOffline"))
    )
    services = list(discovery_redfish_storage(parsed))
    assert len(services) == 0


def test_check_storage_full_mode() -> None:
    parsed = parse_redfish_multiple(_make_string_table(_make_storage_entry()))
    results = list(check_redfish_storage("RAID.Slot.3-1", {}, parsed))
    assert any("PERC H745P" in r.summary for r in results if isinstance(r, Result) and r.summary)


def test_check_storage_rollup_mode() -> None:
    parsed = parse_redfish_multiple(_make_string_table(_make_storage_entry()))
    results = [
        r
        for r in check_redfish_storage("RAID.Slot.3-1", {"check_type": "rollup"}, parsed)
        if isinstance(r, Result)
    ]
    assert len(results) == 1
    assert results[0].state == State.OK


def test_discovery_battery() -> None:
    parsed = parse_redfish_multiple(_make_string_table(_make_storage_entry(battery_status="OK")))
    services = list(discovery_redfish_storage_battery(parsed))
    assert len(services) == 1


def test_discovery_battery_no_oem() -> None:
    parsed = parse_redfish_multiple(_make_string_table(_make_storage_entry()))
    services = list(discovery_redfish_storage_battery(parsed))
    assert len(services) == 0


def test_check_battery_ok() -> None:
    parsed = parse_redfish_multiple(_make_string_table(_make_storage_entry(battery_status="OK")))
    results = [
        r for r in check_redfish_storage_battery("RAID.Slot.3-1", parsed) if isinstance(r, Result)
    ]
    assert results[0].state == State.OK
    assert "OK" in results[0].summary


def test_check_battery_degraded() -> None:
    parsed = parse_redfish_multiple(
        _make_string_table(_make_storage_entry(battery_status="Degraded"))
    )
    results = [
        r for r in check_redfish_storage_battery("RAID.Slot.3-1", parsed) if isinstance(r, Result)
    ]
    assert results[0].state == State.WARN


def test_check_battery_failed() -> None:
    parsed = parse_redfish_multiple(
        _make_string_table(_make_storage_entry(battery_status="Failed"))
    )
    results = [
        r for r in check_redfish_storage_battery("RAID.Slot.3-1", parsed) if isinstance(r, Result)
    ]
    assert results[0].state == State.CRIT
