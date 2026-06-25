#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# NOTE: This file has been created by an LLM (from something that was worse).
# It mostly serves as test to ensure we don't accidentally break anything.
# If you encounter something weird in here, do not hesitate to replace this
# test by something more appropriate.

from collections.abc import Mapping

import pytest

from cmk.agent_based.v2 import Result, State
from cmk.plugins.carel.agent_based.carel_sensors import (
    carel_sensors_parse,
    check_carel_sensors_temp,
    discover_carel_sensors_temp,
)

Section = Mapping[str, float]


def parsed() -> Section:
    """Test parsing of SNMP data for carel_sensors."""
    string_table = [
        ["1.0", "264"],  # Room = 26.4°C
        ["2.0", "0"],  # Outdoor = 0 (filtered out)
        ["3.0", "221"],  # Delivery = 22.1°C
        ["20.0", "220"],  # Cooling Set Point = 22.0°C
        ["21.0", "150"],  # Cooling Prop. Band = 15.0°C
        ["23.0", "170"],  # Heating Set Point = 17.0°C
        ["25.0", "15"],  # Heating Prop. Band = 1.5°C
        ["999.0", "123"],  # Unknown OID (filtered out)
    ]

    return carel_sensors_parse(string_table)


def test_carel_sensors_discovery() -> None:
    discovery_result = list(discover_carel_sensors_temp(parsed()))
    items = [s.item for s in discovery_result]
    assert "Room" in items
    assert "Delivery" in items


def test_carel_sensors_check_room_ok(monkeypatch: pytest.MonkeyPatch) -> None:
    from cmk.plugins.carel.agent_based import carel_sensors

    monkeypatch.setattr(carel_sensors, "get_value_store", dict)

    params = (30.0, 35.0)
    results = list(check_carel_sensors_temp("Room", params, parsed()))

    result_objs = [r for r in results if isinstance(r, Result)]
    assert any(r.state == State.OK for r in result_objs)
    assert any("26.4" in r.summary for r in result_objs)


def test_carel_sensors_check_missing_item(monkeypatch: pytest.MonkeyPatch) -> None:
    from cmk.plugins.carel.agent_based import carel_sensors

    monkeypatch.setattr(carel_sensors, "get_value_store", dict)

    params = (30.0, 35.0)
    results = list(check_carel_sensors_temp("Nonexistent", params, parsed()))
    assert results == []
