#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"

from collections.abc import Sequence

import pytest

from cmk.agent_based.v2 import Metric, Result, State, StringTable
from cmk.plugins.lib.temperature import TempParamDict
from cmk.plugins.pulse_secure.agent_based.pulse_secure_temp import (
    check_pulse_secure_temp,
    discover_pulse_secure_temp,
    parse_pulse_secure_temp,
)


@pytest.fixture
def empty_value_store(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "cmk.plugins.pulse_secure.agent_based.pulse_secure_temp.get_value_store",
        lambda: {},
    )


@pytest.mark.parametrize(
    "string_table, expected_discoveries",
    [
        ([["27"]], [("IVE",)]),
    ],
)
def test_discover_pulse_secure_temp(
    string_table: StringTable, expected_discoveries: Sequence[tuple[str]]
) -> None:
    """Test discovery function for pulse_secure_temp check."""
    parsed = parse_pulse_secure_temp(string_table)
    if parsed is not None:
        result = [(s.item,) for s in discover_pulse_secure_temp(parsed)]
    else:
        result = []
    assert sorted(result) == sorted(expected_discoveries)


@pytest.mark.parametrize(
    "item, params, string_table, expected_state, expected_summary_substring",
    [
        ("IVE", {"levels": (70.0, 75.0)}, [["27"]], State.OK, "27"),
    ],
)
def test_check_pulse_secure_temp(
    item: str,
    params: TempParamDict,
    string_table: StringTable,
    expected_state: State,
    expected_summary_substring: str,
    empty_value_store: None,
) -> None:
    """Test check function for pulse_secure_temp check."""
    parsed = parse_pulse_secure_temp(string_table)
    assert parsed is not None
    results = list(check_pulse_secure_temp(item, params, parsed))
    result_objs = [r for r in results if isinstance(r, Result)]
    metric_objs = [r for r in results if isinstance(r, Metric)]
    assert len(result_objs) >= 1
    assert result_objs[0].state == expected_state
    assert expected_summary_substring in result_objs[0].summary
    assert len(metric_objs) >= 1
