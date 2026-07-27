#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.agent_based.v2 import Metric, Result, State
from cmk.plugins.f5os_rseries.agent_based.fan import (
    check_f5os_rseries_fan,
    discover_f5os_rseries_fan,
    parse_f5os_rseries_fan,
)

# Walk: 8 fans at ~16200 RPM
_FAN_STRING_TABLE = [["16216", "16251", "16198", "16242", "16286", "16233", "16322", "16251"]]


def test_parse_f5os_rseries_fan() -> None:
    section = parse_f5os_rseries_fan(_FAN_STRING_TABLE)
    assert len(section) == 8
    assert abs(section["Fan 1"] - 16216.0) < 0.1
    assert abs(section["Fan 8"] - 16251.0) < 0.1


def test_parse_f5os_rseries_fan_empty() -> None:
    assert parse_f5os_rseries_fan([]) == {}


def test_discover_f5os_rseries_fan() -> None:
    section = parse_f5os_rseries_fan(_FAN_STRING_TABLE)
    services = sorted(discover_f5os_rseries_fan(section), key=lambda s: s.item or "")
    assert [s.item for s in services] == [f"Fan {i}" for i in range(1, 9)]


def test_check_f5os_rseries_fan_ok() -> None:
    section = parse_f5os_rseries_fan(_FAN_STRING_TABLE)
    results = list(
        check_f5os_rseries_fan("Fan 1", {"lower": (5000, 3000), "output_metrics": True}, section)
    )
    assert any(isinstance(r, Result) and r.state == State.OK for r in results)
    assert any(isinstance(r, Metric) and r.name == "fan" for r in results)


def test_check_f5os_rseries_fan_missing_item() -> None:
    section = parse_f5os_rseries_fan(_FAN_STRING_TABLE)
    results = list(
        check_f5os_rseries_fan("Fan 9", {"lower": (5000, 3000), "output_metrics": True}, section)
    )
    assert results == []


def test_parse_f5os_rseries_fan_keeps_stalled_drops_absent() -> None:
    # Fan 3 stalled (reports "0", must stay so it can alert); Fans 7 and 8 not
    # populated on this model (empty string, must be dropped).
    string_table = [["16216", "16251", "0", "16242", "16286", "16233", "", ""]]
    section = parse_f5os_rseries_fan(string_table)
    assert set(section) == {"Fan 1", "Fan 2", "Fan 3", "Fan 4", "Fan 5", "Fan 6"}
    assert section["Fan 3"] == 0.0


def test_parse_f5os_rseries_fan_malformed_raises() -> None:
    # An empty column is a legitimately absent fan slot (skipped), but a *populated*
    # non-numeric value is unexpected and must surface rather than become a phantom 0.
    with pytest.raises(ValueError):
        parse_f5os_rseries_fan([["16216", "N/A", "16198"]])


def test_check_f5os_rseries_fan_stalled_is_crit() -> None:
    # A stalled fan at 0 RPM is below the lower CRIT threshold and must alert.
    section = parse_f5os_rseries_fan([["0", "16251"]])
    results = list(
        check_f5os_rseries_fan("Fan 1", {"lower": (5000, 3000), "output_metrics": True}, section)
    )
    assert any(isinstance(r, Result) and r.state == State.CRIT for r in results)
