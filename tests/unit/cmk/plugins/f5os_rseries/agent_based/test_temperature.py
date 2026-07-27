#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.agent_based.v2 import Metric, Result, Service, State
from cmk.plugins.f5os_rseries.agent_based.temperature import (
    check_f5os_rseries_temp,
    discover_f5os_rseries_temp,
    parse_f5os_rseries_temp,
)

# Walk: single row indexed "platform" (OctetString), values 263/261/257/266 (tenths °C)
# OctetString "platform" = "8.112.108.97.116.102.111.114.109"
_TEMP_OIDEND = "8.112.108.97.116.102.111.114.109"
_TEMP_STRING_TABLE = [[_TEMP_OIDEND, "263", "261", "257", "266"]]


def test_parse_f5os_rseries_temp() -> None:
    result = parse_f5os_rseries_temp(_TEMP_STRING_TABLE)
    assert "platform" in result
    reading = result["platform"]
    assert abs(reading.current - 26.3) < 0.01
    assert abs(reading.average - 26.1) < 0.01
    assert abs(reading.minimum - 25.7) < 0.01
    assert abs(reading.maximum - 26.6) < 0.01


def test_parse_f5os_rseries_temp_empty() -> None:
    assert parse_f5os_rseries_temp([]) == {}


def test_discover_f5os_rseries_temp() -> None:
    section = parse_f5os_rseries_temp(_TEMP_STRING_TABLE)
    assert list(discover_f5os_rseries_temp(section)) == [Service(item="platform")]


def test_check_f5os_rseries_temp_ok() -> None:
    section = parse_f5os_rseries_temp(_TEMP_STRING_TABLE)
    results = list(check_f5os_rseries_temp("platform", {"levels": (35.0, 45.0)}, section))
    assert any(isinstance(r, Result) and r.state == State.OK for r in results)
    assert any(isinstance(r, Metric) and r.name == "temp_avg" for r in results)
    assert any(isinstance(r, Metric) and r.name == "temp_max" for r in results)


def test_check_f5os_rseries_temp_missing_item() -> None:
    section = parse_f5os_rseries_temp(_TEMP_STRING_TABLE)
    results = list(check_f5os_rseries_temp("nonexistent", {"levels": (35.0, 45.0)}, section))
    assert results == []


def test_parse_f5os_rseries_temp_malformed_raises() -> None:
    # An unreadable temperature column is unexpected per the MIB and must surface, not be
    # coerced into a fabricated 0 °C.
    with pytest.raises(ValueError):
        parse_f5os_rseries_temp([[_TEMP_OIDEND, "N/A", "261", "257", "266"]])
