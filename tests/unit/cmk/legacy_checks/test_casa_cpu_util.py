#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"
# mypy: disable-error-code="no-untyped-call"

from collections.abc import Mapping, Sequence
from typing import Any

import pytest
import time_machine

import cmk.legacy_checks.casa_cpu_util as casa_cpu_util_plugin
from cmk.agent_based.v2 import CheckResult, Metric, Result, State, StringTable
from cmk.legacy_checks.casa_cpu_util import (
    check_casa_cpu_util,
    discover_casa_cpu_util,
    parse_casa_cpu_util,
)


@pytest.mark.parametrize(
    ("string_table", "expected_parsed"),
    [
        pytest.param(
            [[["1", "Module 1 QEM"], ["2", "20"]]],
            [[["1", "Module 1 QEM"], ["2", "20"]]],
            id="typical_input",
        ),
        pytest.param(
            [],
            [],
            id="empty_input",
        ),
    ],
)
def test_parse_casa_cpu_util(
    string_table: Sequence[StringTable],
    expected_parsed: Sequence[StringTable],
) -> None:
    assert parse_casa_cpu_util(string_table) == expected_parsed


@pytest.mark.parametrize(
    ("section", "expected_items"),
    [
        pytest.param(
            [
                [["1", "Module 1 QEM"], ["2", "Module 2 QEM"]],
                [["1", "30"], ["2", "20"]],
            ],
            [("Module 1", {}), ("Module 2", {})],
            id="multiple_modules",
        ),
        pytest.param(
            [
                [["1", "Module 1 QEM"]],
                [["1", "30"]],
            ],
            [("Module 1", {})],
            id="single_module",
        ),
        pytest.param(
            [
                [["1", "Module 1 QEM"]],
                [],
            ],
            [],
            id="no_cpu_data",
        ),
    ],
)
def test_discover_casa_cpu_util(
    section: Sequence[StringTable],
    expected_items: list[str],
) -> None:
    assert list(discover_casa_cpu_util(section)) == expected_items  # type: ignore[comparison-overlap,arg-type]


@pytest.mark.parametrize(
    ("item", "params", "section", "expected_output"),
    [
        pytest.param(
            "Module 1",
            {"levels": (80.0, 90.0)},
            [
                [["1", "Module 1 QEM"], ["2", "Module 2 QEM"]],
                [["1", "30"], ["2", "20"]],
            ],
            [
                Result(state=State.OK, summary="Total CPU: 30.00%"),
                Metric("util", 30.0, levels=(80.0, 90.0), boundaries=(0.0, None)),
            ],
            id="ok_below_thresholds",
        ),
        pytest.param(
            "Module 1",
            {"levels": (80.0, 90.0)},
            [
                [["1", "Module 1 QEM"]],
                [["1", "95"]],
            ],
            [
                Result(state=State.CRIT, summary="Total CPU: 95.00% (warn/crit at 80.00%/90.00%)"),
                Metric("util", 95.0, levels=(80.0, 90.0), boundaries=(0.0, None)),
            ],
            id="crit_breaches_threshold",
        ),
        pytest.param(
            "Module 1",
            {"levels": (70.0, 85.0)},
            [
                [["1", "Module 1 QEM"]],
                [["1", "75"]],
            ],
            [
                Result(state=State.WARN, summary="Total CPU: 75.00% (warn/crit at 70.00%/85.00%)"),
                Metric("util", 75.0, levels=(70.0, 85.0), boundaries=(0.0, None)),
            ],
            id="warn_custom_thresholds",
        ),
        pytest.param(
            "Module 1",
            {"levels": (80.0, 90.0), "average": 3},
            [
                [["1", "Module 1 QEM"]],
                [["1", "60"]],
            ],
            [
                Metric("util", 60.0, levels=(80.0, 90.0), boundaries=(0.0, 100.0)),
                Result(state=State.OK, summary="Total CPU (3 min average): 60.00%"),
                Metric("util_average", 60.0, levels=(80.0, 90.0), boundaries=(0.0, None)),
            ],
            id="with_averaging",
        ),
        pytest.param(
            "Module 3",
            {"levels": (80.0, 90.0)},
            [
                [["1", "Module 1 QEM"]],
                [["1", "30"]],
            ],
            [],
            id="item_not_found",
        ),
    ],
)
def test_check_casa_cpu_util(
    item: str,
    params: Mapping[str, Any],
    section: Sequence[StringTable],
    expected_output: CheckResult,
    monkeypatch: pytest.MonkeyPatch,
) -> None:

    value_store: dict[str, Any] = {}
    monkeypatch.setattr(casa_cpu_util_plugin, "get_value_store", lambda: value_store)
    with time_machine.travel("2026-01-01 00:00:00", tick=False):
        result = list(check_casa_cpu_util(item, params, section))

    assert result == expected_output
