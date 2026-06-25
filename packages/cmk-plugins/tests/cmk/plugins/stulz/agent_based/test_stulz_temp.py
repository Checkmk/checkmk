#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc,import-untyped"

import pytest

from cmk.agent_based.v2 import Metric, Result, Service, State
from cmk.plugins.stulz.agent_based import stulz_temp
from cmk.plugins.stulz.agent_based.stulz_temp import (
    check_stulz_temp,
    discover_stulz_temp,
    parse_stulz_temp,
)

# OIDEnd is "{type}.{bus}.{unit}.{subindex}". The 1192 entries cover the same unit number
# (1) on two different buses, which must yield two distinct items (regression for the
# cross-bus naming collision).
_STRING_TABLE: list[list[str]] = [
    ["1170.1.1.1", "220"],
    ["1192.1.1.1", "221"],
    ["1192.2.1.1", "248"],
    ["1196.1.2.1", "999"],
    ["99999.1.1.1", "300"],
]


@pytest.fixture
def _patch_value_store(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(stulz_temp, "get_value_store", dict)


def test_parse_stulz_temp_filters_sentinel_and_unknown_types() -> None:
    assert parse_stulz_temp(_STRING_TABLE) == {
        "unit air 1-1": 22.0,
        "unit return air 1-1": 22.1,
        "unit return air 2-1": 24.8,
    }


def test_discover_stulz_temp() -> None:
    section = parse_stulz_temp(_STRING_TABLE)
    assert list(discover_stulz_temp(section)) == [
        Service(item="unit air 1-1"),
        Service(item="unit return air 1-1"),
        Service(item="unit return air 2-1"),
    ]


def test_check_stulz_temp_ok(_patch_value_store: None) -> None:
    section = parse_stulz_temp(_STRING_TABLE)
    results = list(check_stulz_temp("unit air 1-1", {"levels": (25.0, 28.0)}, section))
    assert any(
        isinstance(r, Result) and r.state is State.OK and "22.0" in r.summary for r in results
    )
    assert any(isinstance(r, Metric) and r.name == "temp" and r.value == 22.0 for r in results)


def test_check_stulz_temp_crit(_patch_value_store: None) -> None:
    section = {"unit air 1-1": 30.0}
    results = list(check_stulz_temp("unit air 1-1", {"levels": (25.0, 28.0)}, section))
    assert any(isinstance(r, Result) and r.state is State.CRIT for r in results)


def test_check_stulz_temp_missing_item(_patch_value_store: None) -> None:
    section = parse_stulz_temp(_STRING_TABLE)
    assert list(check_stulz_temp("does-not-exist", {"levels": (25.0, 28.0)}, section)) == []
