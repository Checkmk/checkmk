#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"

from collections.abc import Sequence

import pytest

from cmk.agent_based.v2 import Metric, Result, Service, State, StringTable
from cmk.plugins.hwg.agent_based import hwg_temp
from cmk.plugins.hwg.agent_based.hwg_temp import check_hwg_temp, discover_hwg_temp
from cmk.plugins.hwg.agent_based.lib import parse_hwg
from cmk.plugins.lib.temperature import TempParamType


@pytest.fixture(autouse=True)
def _patch_value_store(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(hwg_temp, "get_value_store", lambda: {})


@pytest.mark.parametrize(
    "info, expected_discoveries",
    [
        (
            [["1", "Netzwerk-Rack", "1", "23.8", "1"], ["2", "Library-Rack", "1", "23.0", "1"]],
            [Service(item="1"), Service(item="2")],
        ),
    ],
)
def test_discover_hwg_temp(info: StringTable, expected_discoveries: Sequence[Service]) -> None:
    """Test discovery function for hwg_temp check."""
    parsed = parse_hwg(info)
    result = list(discover_hwg_temp(parsed))
    assert sorted(result, key=lambda s: s.item or "") == sorted(
        expected_discoveries, key=lambda s: s.item or ""
    )


@pytest.mark.parametrize(
    "item, params, info, expected_state, expected_summary_fragment",
    [
        pytest.param(
            "1",
            {"levels": (30.0, 35.0)},
            [["1", "Netzwerk-Rack", "1", "23.8", "1"], ["2", "Library-Rack", "1", "23.0", "1"]],
            State.OK,
            "23.8",
            id="sensor_1",
        ),
        pytest.param(
            "2",
            {"levels": (30.0, 35.0)},
            [["1", "Netzwerk-Rack", "1", "23.8", "1"], ["2", "Library-Rack", "1", "23.0", "1"]],
            State.OK,
            "23.0",
            id="sensor_2",
        ),
    ],
)
def test_check_hwg_temp(
    item: str,
    params: TempParamType,
    info: StringTable,
    expected_state: State,
    expected_summary_fragment: str,
) -> None:
    """Test check function for hwg_temp check."""
    parsed = parse_hwg(info)
    results = list(check_hwg_temp(item, params, parsed))

    # Should contain Result and Metric objects
    result_objs = [r for r in results if isinstance(r, Result)]
    metric_objs = [r for r in results if isinstance(r, Metric)]

    assert len(result_objs) >= 1
    assert len(metric_objs) >= 1

    # Check the reading result contains the temperature
    reading_result = result_objs[0]
    assert reading_result.state == expected_state
    assert expected_summary_fragment in reading_result.summary

    # Check the description result
    desc_result = result_objs[-1]
    assert "Description:" in desc_result.summary
    assert "Status:" in desc_result.summary

    # Check the metric
    assert metric_objs[0].name == "temp"
