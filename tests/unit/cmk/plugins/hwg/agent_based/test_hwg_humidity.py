#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

import pytest

from cmk.agent_based.internal import evaluate_snmp_detection
from cmk.agent_based.v2 import Metric, Result, Service, State, StringTable
from cmk.plugins.hwg.agent_based.hwg_humidity import (
    check_hwg_humidity,
    discover_hwg_humidity,
    snmp_section_hwg_humidity,
)
from cmk.plugins.hwg.agent_based.lib import parse_hwg


def test_detect_hwg_humidity() -> None:
    assert (detect_spec := snmp_section_hwg_humidity.detect)
    assert evaluate_snmp_detection(
        detect_spec=detect_spec,
        oid_value_getter={".1.3.6.1.2.1.1.1.0": "contains lower HWG"}.get,
    )


@pytest.mark.parametrize(
    "info, expected_discoveries",
    [
        (
            [["1", "Sensor 215", "1", "23.8", "1"], ["2", "Sensor 216", "1", "34.6", "4"]],
            [Service(item="2")],
        ),
    ],
)
def test_discover_hwg_humidity(info: StringTable, expected_discoveries: Sequence[Service]) -> None:
    """Test discovery function for hwg_humidity check."""
    parsed = parse_hwg(info)
    result = list(discover_hwg_humidity(parsed))
    assert sorted(result, key=lambda s: s.item or "") == sorted(
        expected_discoveries, key=lambda s: s.item or ""
    )


@pytest.mark.parametrize(
    "item, params, info, expected_results",
    [
        (
            "2",
            {"levels": (60.0, 70.0)},
            [["1", "Sensor 215", "1", "23.8", "1"], ["2", "Sensor 216", "1", "34.6", "4"]],
            [
                Result(state=State.OK, summary="34.60%"),
                Metric("humidity", 34.6, levels=(60.0, 70.0), boundaries=(0.0, 100.0)),
                Result(
                    state=State.OK,
                    summary="Description: Sensor 216, Status: normal",
                ),
            ],
        ),
    ],
)
def test_check_hwg_humidity(
    item: str,
    params: Mapping[str, float],
    info: StringTable,
    expected_results: Sequence[Result | Metric],
) -> None:
    """Test check function for hwg_humidity check."""
    parsed = parse_hwg(info)
    result = list(check_hwg_humidity(item, params, parsed))
    assert result == expected_results
