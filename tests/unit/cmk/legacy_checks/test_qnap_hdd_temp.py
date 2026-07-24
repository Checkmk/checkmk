#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

import pytest

import cmk.legacy_checks.qnap_hdd_temp as qnap_hdd_temp_plugin
from cmk.agent_based.v2 import Metric, Result, Service, State
from cmk.legacy_checks.qnap_hdd_temp import (
    check_qqnap_hdd_temp,
    discover_qnap_hdd_temp,
    parse_qnap_hdd_temp,
)

_STRING_TABLE = [
    ["HDD1", "37 C/98 F"],
    ["HDD2", "32 C/89 F"],
    ["HDD3", "40 C/104 F"],
    ["HDD4", "39 C/102 F"],
    ["HDD5", "45 C/113 F"],
    ["HDD6", "43 C/109 F"],
]

_CONFIG_NOTICE = Result(
    state=State.OK,
    notice="Configuration: prefer user levels over device levels (used user levels)",
)


def test_discover_qnap_hdd_temp() -> None:
    """Test discovery function for qnap_hdd_temp check."""
    parsed = parse_qnap_hdd_temp(_STRING_TABLE)
    result = list(discover_qnap_hdd_temp(parsed))
    assert result == [
        Service(item="HDD1"),
        Service(item="HDD2"),
        Service(item="HDD3"),
        Service(item="HDD4"),
        Service(item="HDD5"),
        Service(item="HDD6"),
    ]


@pytest.mark.parametrize(
    "item, expected_results",
    [
        (
            "HDD1",
            [
                Metric("temp", 37.0, levels=(40.0, 45.0)),
                Result(state=State.OK, summary="Temperature: 37.0 °C"),
                _CONFIG_NOTICE,
            ],
        ),
        (
            "HDD2",
            [
                Metric("temp", 32.0, levels=(40.0, 45.0)),
                Result(state=State.OK, summary="Temperature: 32.0 °C"),
                _CONFIG_NOTICE,
            ],
        ),
        (
            "HDD3",
            [
                Metric("temp", 40.0, levels=(40.0, 45.0)),
                Result(state=State.WARN, summary="Temperature: 40.0 °C (warn/crit at 40 °C/45 °C)"),
                _CONFIG_NOTICE,
            ],
        ),
        (
            "HDD4",
            [
                Metric("temp", 39.0, levels=(40.0, 45.0)),
                Result(state=State.OK, summary="Temperature: 39.0 °C"),
                _CONFIG_NOTICE,
            ],
        ),
        (
            "HDD5",
            [
                Metric("temp", 45.0, levels=(40.0, 45.0)),
                Result(state=State.CRIT, summary="Temperature: 45.0 °C (warn/crit at 40 °C/45 °C)"),
                _CONFIG_NOTICE,
            ],
        ),
        (
            "HDD6",
            [
                Metric("temp", 43.0, levels=(40.0, 45.0)),
                Result(state=State.WARN, summary="Temperature: 43.0 °C (warn/crit at 40 °C/45 °C)"),
                _CONFIG_NOTICE,
            ],
        ),
    ],
)
def test_check_qnap_hdd_temp(
    item: str,
    expected_results: Sequence[Result | Metric],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test check function for qnap_hdd_temp check."""
    value_store: dict[str, object] = {}
    monkeypatch.setattr(qnap_hdd_temp_plugin, "get_value_store", lambda: value_store)
    parsed = parse_qnap_hdd_temp(_STRING_TABLE)
    result = list(check_qqnap_hdd_temp(item, {"levels": (40, 45)}, parsed))
    assert result == expected_results
