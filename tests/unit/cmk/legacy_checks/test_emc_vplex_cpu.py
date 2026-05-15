#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"

from collections.abc import Mapping
from typing import Any

import pytest
import time_machine

import cmk.plugins.emc.agent_based.emc_vplex_cpu as emc_vplex_cpu_plugin
from cmk.agent_based.v2 import CheckResult, Metric, Result, Service, State, StringTable
from cmk.plugins.emc.agent_based.emc_vplex_cpu import (
    check_emc_vplex_cpu,
    discover_emc_vplex_cpu,
    parse_emc_vplex_cpu,
)


@pytest.mark.parametrize(
    ("string_table", "expected_parsed"),
    [
        pytest.param(
            [["director1", "70"], ["director2", "40"]],
            {"director1": 70, "director2": 40},
            id="multiple_directors",
        ),
        pytest.param(
            [["director1", "0"]],
            {"director1": 0},
            id="zero_utilization",
        ),
        pytest.param(
            [],
            {},
            id="empty_input",
        ),
    ],
)
def test_parse_emc_vplex_cpu(
    string_table: StringTable,
    expected_parsed: Mapping[str, int],
) -> None:
    assert parse_emc_vplex_cpu(string_table) == expected_parsed


def test_discover_emc_vplex_cpu() -> None:
    section = {"director1": 70, "director2": 40}
    assert sorted(discover_emc_vplex_cpu(section)) == sorted(
        [Service(item="director1"), Service(item="director2")]
    )


@pytest.mark.parametrize(
    ("params", "section", "expected_output"),
    [
        pytest.param(
            {"levels": (90.0, 95.0)},
            {"director1": 70},
            [
                Result(state=State.OK, summary="Total CPU: 30.00%"),
                Metric("util", 30.0, levels=(90.0, 95.0), boundaries=(0.0, None)),
            ],
            id="ok_below_thresholds",
        ),
        pytest.param(
            {"levels": (90.0, 95.0)},
            {"director1": 1},
            [
                Result(state=State.CRIT, summary="Total CPU: 99.00% (warn/crit at 90.00%/95.00%)"),
                Metric("util", 99.0, levels=(90.0, 95.0), boundaries=(0.0, None)),
            ],
            id="crit_breaches_threshold",
        ),
        pytest.param(
            {"levels": (80.0, 90.0)},
            {"director1": 15},
            [
                Result(state=State.WARN, summary="Total CPU: 85.00% (warn/crit at 80.00%/90.00%)"),
                Metric("util", 85.0, levels=(80.0, 90.0), boundaries=(0.0, None)),
            ],
            id="warn_custom_thresholds",
        ),
        pytest.param(
            {"levels": (90.0, 95.0), "average": 3},
            {"director1": 40},
            [
                Metric("util", 60.0, levels=(90.0, 95.0), boundaries=(0.0, 100.0)),
                Result(state=State.OK, summary="Total CPU (3 min average): 60.00%"),
                Metric("util_average", 60.0, levels=(90.0, 95.0), boundaries=(0.0, None)),
            ],
            id="with_averaging",
        ),
        pytest.param(
            {"levels": (90.0, 95.0)},
            {"not_queried": 70},
            [],
            id="item_not_found",
        ),
    ],
)
def test_check_emc_vplex_cpu(
    params: Mapping[str, Any],
    section: Mapping[str, int],
    expected_output: CheckResult,
    monkeypatch: pytest.MonkeyPatch,
) -> None:

    item = "director1"
    value_store: Mapping[str, Any] = {}
    monkeypatch.setattr(emc_vplex_cpu_plugin, "get_value_store", lambda: value_store)
    with time_machine.travel("2026-01-01 00:00:00", tick=False):
        result = list(check_emc_vplex_cpu(item, params, section))

    assert result == expected_output
