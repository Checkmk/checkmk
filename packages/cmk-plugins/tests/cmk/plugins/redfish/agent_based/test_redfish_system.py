#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from typing import Any

from cmk.agent_based.v2 import Result, State, StringTable
from cmk.plugins.redfish.agent_based.redfish_system import (
    check_redfish_system,
    parse_redfish_system,
)


def _make_system_string_table(
    system_id: str = "System.Embedded.1",
    *,
    serial: str | None = "ULIWGEYN532YXP",
    sku: str | None = "ABC1234",
    health: str = "OK",
    state: str = "Enabled",
    dell_oem: bool = False,
) -> StringTable:
    entry: dict[str, Any] = {
        "Id": system_id,
        "Name": "System",
        "Status": {"Health": health, "HealthRollup": health, "State": state},
    }
    if serial:
        entry["SerialNumber"] = serial
    if sku:
        entry["SKU"] = sku
    if dell_oem:
        entry["Oem"] = {
            "Dell": {
                "DellSystem": {
                    "ChassisServiceTag": "ABC1234",
                    "BatteryRollupStatus": "OK",
                    "CPURollupStatus": "OK",
                    "PSRollupStatus": "OK",
                    "StorageRollupStatus": "OK",
                }
            }
        }
    return [[json.dumps([entry])]]


def test_check_system_basic() -> None:
    section = parse_redfish_system(_make_system_string_table())
    assert section is not None
    results = list(check_redfish_system("System.Embedded.1", section))
    assert any(
        isinstance(r, Result) and "Serial Number: ULIWGEYN532YXP" in (r.summary or "")
        for r in results
    )


def test_check_system_with_dell_oem() -> None:
    section = parse_redfish_system(_make_system_string_table(dell_oem=True))
    assert section is not None
    results = list(check_redfish_system("System.Embedded.1", section))
    # Should have serial + health results
    summaries = [r.summary for r in results if isinstance(r, Result) and r.summary]
    assert any("Serial" in s for s in summaries)
    # Should have Dell OEM details
    details = [r.details for r in results if isinstance(r, Result) and r.details]
    assert any("Rollup" in d for d in details)


def test_check_system_critical_health() -> None:
    section = parse_redfish_system(_make_system_string_table(health="Critical"))
    assert section is not None
    results = list(check_redfish_system("System.Embedded.1", section))
    assert any(r.state == State.CRIT for r in results if isinstance(r, Result))


def test_check_system_item_not_found() -> None:
    section = parse_redfish_system(_make_system_string_table())
    assert section is not None
    results = list(check_redfish_system("nonexistent", section))
    assert results == []
