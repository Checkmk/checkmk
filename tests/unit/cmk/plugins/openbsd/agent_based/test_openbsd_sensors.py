#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"

from unittest.mock import patch

import pytest

from cmk.agent_based.v2 import Metric, Result, Service, State, StringTable
from cmk.plugins.openbsd.agent_based.openbsd_sensors import (
    check_openbsd_sensors,
    discover_openbsd_sensors,
    parse_openbsd_sensors,
)

STRING_TABLE: StringTable = [
    ["temp0", "0", "30.00", "degC", "0"],
    ["sd0", "13", "online", "", "1"],
    ["CPU1 Temp", "0", "35.00", "degC", "1"],
    ["CPU2 Temp", "0", "36.00", "degC", "1"],
    ["PCH Temp", "0", "36.00", "degC", "1"],
    ["System Temp", "0", "23.00", "degC", "1"],
    ["Peripheral Temp", "0", "34.00", "degC", "1"],
    ["Vcpu1VRM Temp", "0", "30.00", "degC", "1"],
    ["Vcpu2VRM Temp", "0", "34.00", "degC", "1"],
    ["VmemABVRM Temp", "0", "26.00", "degC", "1"],
    ["VmemCDVRM Temp", "0", "34.00", "degC", "1"],
    ["VmemEFVRM Temp", "0", "29.00", "degC", "1"],
    ["VmemGHVRM Temp", "0", "28.00", "degC", "1"],
    ["P1-DIMMA1 Temp", "0", "25.00", "degC", "1"],
    ["P1-DIMMB1 Temp", "0", "25.00", "degC", "1"],
    ["P1-DIMMC1 Temp", "0", "26.00", "degC", "1"],
    ["P1-DIMMD1 Temp", "0", "24.00", "degC", "1"],
    ["P2-DIMME1 Temp", "0", "28.00", "degC", "1"],
    ["P2-DIMMF1 Temp", "0", "26.00", "degC", "1"],
    ["P2-DIMMG1 Temp", "0", "27.00", "degC", "1"],
    ["P2-DIMMH1 Temp", "0", "28.00", "degC", "1"],
    ["MB/AOM_SAS Temp", "0", "46.00", "degC", "1"],
    ["FAN1", "1", "3100", "RPM", "1"],
    ["FAN3", "1", "3100", "RPM", "1"],
    ["FANA", "1", "2600", "RPM", "1"],
    ["12V", "2", "12.06", "V DC", "1"],
    ["5VCC", "2", "5.08", "V DC", "1"],
    ["3.3VCC", "2", "3.38", "V DC", "1"],
    ["VBAT", "2", "2.98", "V DC", "1"],
    ["Vcpu1", "2", "1.84", "V DC", "1"],
    ["Vcpu2", "2", "1.84", "V DC", "1"],
    ["VDIMMAB", "2", "1.21", "V DC", "1"],
    ["VDIMMCD", "2", "1.21", "V DC", "1"],
    ["VDIMMEF", "2", "1.21", "V DC", "1"],
    ["VDIMMGH", "2", "1.21", "V DC", "1"],
    ["5VSB", "2", "4.97", "V DC", "1"],
    ["3.3VSB", "2", "3.30", "V DC", "1"],
    ["1.5V PCH", "2", "1.52", "V DC", "1"],
    ["1.2V BMC", "2", "1.22", "V DC", "1"],
    ["1.05V PCH", "2", "1.06", "V DC", "1"],
    ["Chassis Intru", "9", "off", "", "1"],
    ["PS1 Status", "21", "present", "", "1"],
    ["PS2 Status", "21", "present", "", "1"],
]


def test_discover_openbsd_sensors() -> None:
    """Test discovery function for openbsd_sensors check."""
    parsed = parse_openbsd_sensors(STRING_TABLE)
    result = sorted(discover_openbsd_sensors(parsed), key=lambda s: s.item or "")
    expected = sorted(
        [
            Service(item="CPU1 Temp"),
            Service(item="CPU2 Temp"),
            Service(item="MB/AOM_SAS Temp"),
            Service(item="P1-DIMMA1 Temp"),
            Service(item="P1-DIMMB1 Temp"),
            Service(item="P1-DIMMC1 Temp"),
            Service(item="P1-DIMMD1 Temp"),
            Service(item="P2-DIMME1 Temp"),
            Service(item="P2-DIMMF1 Temp"),
            Service(item="P2-DIMMG1 Temp"),
            Service(item="P2-DIMMH1 Temp"),
            Service(item="PCH Temp"),
            Service(item="Peripheral Temp"),
            Service(item="System Temp"),
            Service(item="Vcpu1VRM Temp"),
            Service(item="Vcpu2VRM Temp"),
            Service(item="VmemABVRM Temp"),
            Service(item="VmemCDVRM Temp"),
            Service(item="VmemEFVRM Temp"),
            Service(item="VmemGHVRM Temp"),
            Service(item="temp0"),
        ],
        key=lambda s: s.item or "",
    )
    assert result == expected


@pytest.mark.parametrize(
    "item, expected_temp",
    [
        ("CPU1 Temp", 35.0),
        ("CPU2 Temp", 36.0),
        ("MB/AOM_SAS Temp", 46.0),
        ("P1-DIMMA1 Temp", 25.0),
        ("P1-DIMMB1 Temp", 25.0),
        ("P1-DIMMC1 Temp", 26.0),
        ("P1-DIMMD1 Temp", 24.0),
        ("P2-DIMME1 Temp", 28.0),
        ("P2-DIMMF1 Temp", 26.0),
        ("P2-DIMMG1 Temp", 27.0),
        ("P2-DIMMH1 Temp", 28.0),
        ("PCH Temp", 36.0),
        ("Peripheral Temp", 34.0),
        ("System Temp", 23.0),
        ("Vcpu1VRM Temp", 30.0),
        ("Vcpu2VRM Temp", 34.0),
        ("VmemABVRM Temp", 26.0),
        ("VmemCDVRM Temp", 34.0),
        ("VmemEFVRM Temp", 29.0),
        ("VmemGHVRM Temp", 28.0),
        ("temp0", 30.0),
    ],
)
@patch("cmk.plugins.openbsd.agent_based.openbsd_sensors.get_value_store", return_value={})
def test_check_openbsd_sensors(_mock_value_store: object, item: str, expected_temp: float) -> None:
    """Test check function for openbsd_sensors check."""
    parsed = parse_openbsd_sensors(STRING_TABLE)
    results = list(check_openbsd_sensors(item, {}, parsed))
    metrics = [r for r in results if isinstance(r, Metric)]
    state_results = [r for r in results if isinstance(r, Result)]

    assert any(m.name == "temp" and m.value == expected_temp for m in metrics)
    assert any(r.state == State.OK for r in state_results)


@patch("cmk.plugins.openbsd.agent_based.openbsd_sensors.get_value_store", return_value={})
def test_check_openbsd_sensors_not_found(_mock_value_store: object) -> None:
    """Test check function returns nothing for non-existent item."""
    parsed = parse_openbsd_sensors(STRING_TABLE)
    results = list(check_openbsd_sensors("nonexistent", {}, parsed))
    assert results == []
