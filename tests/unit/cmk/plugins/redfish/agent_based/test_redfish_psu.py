#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from typing import Any

from cmk.agent_based.v2 import Metric, Result, StringTable
from cmk.plugins.redfish.agent_based.redfish_psu import (
    check_redfish_psu,
    discovery_redfish_psu,
)
from cmk.plugins.redfish.lib import parse_redfish_multiple, RedfishAPIData


def _power_section(*supplies: dict[str, Any]) -> RedfishAPIData:
    entry = {
        "@odata.id": "/redfish/v1/Chassis/System.Embedded.1/Power",
        "@odata.type": "#Power.v1_7_1.Power",
        "Id": "Power",
        "PowerSupplies": list(supplies),
    }
    string_table: StringTable = [[json.dumps(entry)]]
    return parse_redfish_multiple(string_table)


def test_discovery_does_not_crash_on_missing_name() -> None:
    # A reference-only PowerSupply stub without "Name" used to raise KeyError and
    # crash the whole host discovery (CMK-34637). It must no longer raise, and the
    # fallback Name -> MemberId -> Id must produce the right items.
    section = _power_section(
        {"Name": "PS1 Status", "Status": {"State": "Enabled"}},
        {"MemberId": "1", "Status": {"State": "Enabled"}},  # no Name -> MemberId
        {"Id": "PSU.Slot.3", "Status": {"State": "Enabled"}},  # no Name/MemberId -> Id
        {"Status": {"State": "Enabled"}},  # reference-only stub: no identity -> skipped
        {"Name": "PS5", "Status": {"State": "Absent"}},  # Absent -> skipped
    )

    items = [service.item for service in discovery_redfish_psu(section)]

    assert items == ["0-PS1 Status", "1-1", "2-PSU.Slot.3"]


def test_discovery_skips_disabled_supply() -> None:
    section = _power_section({"Name": "PS1", "Status": {"State": "Disabled"}})
    assert list(discovery_redfish_psu(section)) == []


def test_discovery_empty_name_falls_back_to_memberid() -> None:
    # An explicit empty/falsy "Name" is treated as absent (accepted side effect).
    section = _power_section({"Name": "", "MemberId": "0", "Status": {"State": "Enabled"}})
    assert [service.item for service in discovery_redfish_psu(section)] == ["0-0"]


def test_check_matches_item_discovered_via_fallback() -> None:
    # An item discovered via the MemberId fallback ("1-1") must be matched by the
    # check function and yield its metrics (discovery <-> check naming consistency).
    section = _power_section(
        {"Name": "PS1", "Status": {"State": "Enabled", "Health": "OK"}},
        {
            "MemberId": "1",
            "Status": {"State": "Enabled", "Health": "OK"},
            "PowerInputWatts": 120.0,
            "PowerOutputWatts": 100.0,
            "LineInputVoltage": 230.0,
            "PowerCapacityWatts": 750.0,
            "Model": "PWR SPLY",
        },
    )

    results = list(check_redfish_psu("1-1", section))

    metrics = {m.name: m.value for m in results if isinstance(m, Metric)}
    assert metrics == {"input_power": 120.0, "output_power": 100.0, "input_voltage": 230.0}
    assert any(isinstance(r, Result) and "100.0 Watts output" in r.summary for r in results)


def test_check_unknown_item_returns_nothing() -> None:
    section = _power_section({"Name": "PS1", "Status": {"State": "Enabled"}})
    assert list(check_redfish_psu("does-not-exist", section)) == []
