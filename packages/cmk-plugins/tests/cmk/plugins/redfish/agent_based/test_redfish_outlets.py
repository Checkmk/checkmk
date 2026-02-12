#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json

import pytest

from cmk.agent_based.v2 import Metric, Result, State, StringTable
from cmk.plugins.redfish.agent_based.redfish_outlets import check_redfish_outlets
from cmk.plugins.redfish.lib import parse_redfish_multiple


def _make_outlet_entry(
    outlet_id: str,
    *,
    voltage: float | None = None,
    current: float | None = None,
    power: float | None = None,
    frequency: float | None = None,
    energy: float | None = None,
    health: str = "OK",
    state: str = "Enabled",
) -> str:
    entry: dict[str, object] = {
        "@odata.id": f"/redfish/v1/PowerEquipment/RackPDUs/1/Outlets/{outlet_id}",
        "@odata.type": "#Outlet.v1_4_0.Outlet",
        "Id": outlet_id,
        "Name": f"Outlet {outlet_id}",
        "Status": {"Health": health, "State": state},
        "Voltage": {"Reading": voltage},
        "CurrentAmps": {"Reading": current},
        "PowerWatts": {"Reading": power},
        "FrequencyHz": {"Reading": frequency},
        "EnergykWh": {"Reading": energy},
        "UserLabel": "",
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
                _make_outlet_entry(
                    "1",
                    voltage=230.5,
                    current=0.8,
                    power=184.4,
                    frequency=50.0,
                    health="OK",
                    state="Enabled",
                ),
            ),
            [
                Result(state=State.OK, summary="Voltage: 230.5 V"),
                Metric("voltage", 230.5),
                Result(state=State.OK, summary="Current: 0.8 A"),
                Metric("current", 0.8),
                Result(state=State.OK, summary="Power: 184.4 W"),
                Metric("power", 184.4),
                Result(state=State.OK, summary="Frequency: 50.0 Hz"),
                Metric("frequency", 50.0),
                Result(
                    state=State.OK,
                    notice="Component State: Normal, This resource is enabled.",
                ),
            ],
            id="numeric_id",
        ),
        pytest.param(
            "01",
            _make_string_table(
                _make_outlet_entry(
                    "1",
                    voltage=230.5,
                    current=0.8,
                    power=184.4,
                    frequency=50.0,
                ),
            ),
            [
                Result(state=State.OK, summary="Voltage: 230.5 V"),
                Metric("voltage", 230.5),
                Result(state=State.OK, summary="Current: 0.8 A"),
                Metric("current", 0.8),
                Result(state=State.OK, summary="Power: 184.4 W"),
                Metric("power", 184.4),
                Result(state=State.OK, summary="Frequency: 50.0 Hz"),
                Metric("frequency", 50.0),
                Result(
                    state=State.OK,
                    notice="Component State: Normal, This resource is enabled.",
                ),
            ],
            id="zero_padded_numeric_id",
        ),
        pytest.param(
            "3-ServerRack",
            _make_string_table(
                _make_outlet_entry(
                    "3",
                    voltage=231.0,
                    current=1.2,
                    power=277.2,
                    frequency=50.0,
                ),
            ),
            [
                Result(state=State.OK, summary="Voltage: 231.0 V"),
                Metric("voltage", 231.0),
                Result(state=State.OK, summary="Current: 1.2 A"),
                Metric("current", 1.2),
                Result(state=State.OK, summary="Power: 277.2 W"),
                Metric("power", 277.2),
                Result(state=State.OK, summary="Frequency: 50.0 Hz"),
                Metric("frequency", 50.0),
                Result(
                    state=State.OK,
                    notice="Component State: Normal, This resource is enabled.",
                ),
            ],
            id="label_format_id",
        ),
        pytest.param(
            "L3_F2_30",
            _make_string_table(
                _make_outlet_entry(
                    "L3_F2_30",
                    voltage=229.8,
                    current=0.5,
                    power=114.9,
                    frequency=50.0,
                ),
            ),
            [
                Result(state=State.OK, summary="Voltage: 229.8 V"),
                Metric("voltage", 229.8),
                Result(state=State.OK, summary="Current: 0.5 A"),
                Metric("current", 0.5),
                Result(state=State.OK, summary="Power: 114.9 W"),
                Metric("power", 114.9),
                Result(state=State.OK, summary="Frequency: 50.0 Hz"),
                Metric("frequency", 50.0),
                Result(
                    state=State.OK,
                    notice="Component State: Normal, This resource is enabled.",
                ),
            ],
            id="alphanumeric_id_rittal_pdu",
        ),
        pytest.param(
            "L1_F1_10",
            _make_string_table(
                _make_outlet_entry(
                    "L1_F1_10",
                    health="Critical",
                    state="Enabled",
                ),
            ),
            [
                Result(
                    state=State.CRIT,
                    notice="Component State: A critical condition requires immediate attention., This resource is enabled.",
                ),
            ],
            id="alphanumeric_id_critical_health",
        ),
        pytest.param(
            "nonexistent",
            _make_string_table(
                _make_outlet_entry("1"),
            ),
            [],
            id="item_not_found",
        ),
    ],
)
def test_check_redfish_outlets(
    item: str, string_table: StringTable, expected: list[Result | Metric]
) -> None:
    parsed = parse_redfish_multiple(string_table)
    assert expected == list(check_redfish_outlets(item, {}, parsed))
