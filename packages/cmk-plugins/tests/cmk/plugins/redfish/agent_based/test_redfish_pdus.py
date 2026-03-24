#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from typing import Any

import pytest

from cmk.agent_based.v2 import Result, State, StringTable
from cmk.plugins.redfish.agent_based.redfish_pdus import (
    check_redfish_pdus,
    discovery_redfish_pdus,
)
from cmk.plugins.redfish.lib import parse_redfish_multiple


def _make_pdu_entry(
    pdu_id: str,
    *,
    manufacturer: str = "Raritan",
    model: str = "PX4-559A-E8",
    serial: str = "R2AB0001172",
    firmware: str = "4.2.0.5-50274",
    health: str = "OK",
    state: str = "Enabled",
) -> str:
    entry: dict[str, Any] = {
        "@odata.id": f"/redfish/v1/PowerEquipment/RackPDUs/{pdu_id}",
        "@odata.type": "#PowerDistribution.v1_2_2.PowerDistribution",
        "Id": pdu_id,
        "Name": f"PDU {pdu_id}",
        "Manufacturer": manufacturer,
        "Model": model,
        "SerialNumber": serial,
        "FirmwareVersion": firmware,
        "Status": {"Health": health, "State": state, "HealthRollup": health},
    }
    return json.dumps(entry)


def _make_string_table(*entries: str) -> StringTable:
    return [[e] for e in entries]


@pytest.mark.parametrize(
    ["item", "string_table", "expected"],
    [
        pytest.param(
            "1",
            _make_string_table(
                _make_pdu_entry("1"),
            ),
            [
                Result(
                    state=State.OK,
                    summary="Firmware: 4.2.0.5-50274, Serial: R2AB0001172, "
                    "Model: PX4-559A-E8, Manufacturer: Raritan",
                ),
                Result(
                    state=State.OK,
                    notice="Component State: Normal, "
                    "This resource is enabled., "
                    "Rollup State: Normal",
                ),
            ],
            id="ok_pdu",
        ),
        pytest.param(
            "1",
            _make_string_table(
                _make_pdu_entry("1", health="Critical"),
            ),
            [
                Result(
                    state=State.OK,
                    summary="Firmware: 4.2.0.5-50274, Serial: R2AB0001172, "
                    "Model: PX4-559A-E8, Manufacturer: Raritan",
                ),
                Result(
                    state=State.CRIT,
                    notice="Component State: A critical condition requires immediate attention., "
                    "This resource is enabled., "
                    "Rollup State: A critical condition requires immediate attention.",
                ),
            ],
            id="critical_pdu",
        ),
        pytest.param(
            "nonexistent",
            _make_string_table(
                _make_pdu_entry("1"),
            ),
            [],
            id="item_not_found",
        ),
    ],
)
def test_check_redfish_pdus(item: str, string_table: StringTable, expected: list[Result]) -> None:
    parsed = parse_redfish_multiple(string_table)
    assert expected == list(check_redfish_pdus(item, parsed))


def test_missing_id_falls_back_to_key() -> None:
    """Discovery and check must agree on item name when Id is missing."""
    entry: dict[str, Any] = {
        "@odata.id": "/redfish/v1/PowerEquipment/RackPDUs/1",
        "@odata.type": "#PowerDistribution.v1_2_2.PowerDistribution",
        "Name": "PDU 1",
        "Status": {"Health": "OK", "State": "Enabled"},
    }
    string_table: StringTable = [[json.dumps(entry)]]
    parsed = parse_redfish_multiple(string_table)

    services = list(discovery_redfish_pdus(parsed))
    assert len(services) == 1
    assert services[0].item is not None

    results = list(check_redfish_pdus(services[0].item, parsed))
    assert len(results) > 0
