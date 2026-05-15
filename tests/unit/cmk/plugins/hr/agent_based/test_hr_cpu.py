#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"

from collections.abc import Mapping
from typing import Any

import pytest
import time_machine

import cmk.plugins.hr.agent_based.hr_cpu as hr_cpu_plugin
from cmk.agent_based.v2 import CheckResult, Metric, Result, Service, State, StringTable
from cmk.plugins.hr.agent_based.hr_cpu import (
    check_hr_cpu,
    discover_hr_cpu,
    parse_hr_cpu,
)


def test_discover_hr_cpu() -> None:
    parsed = parse_hr_cpu([["20"], ["30"]])
    assert list(discover_hr_cpu(parsed)) == [Service()]


@pytest.mark.parametrize(
    ("params", "parsed", "expected_output"),
    [
        pytest.param(
            {"util": (80.0, 90.0)},
            [["20"], ["30"]],
            [
                Result(state=State.OK, summary="Total CPU: 25.00%"),
                Metric("util", 25.0, levels=(80.0, 90.0), boundaries=(0.0, None)),
            ],
            id="ok_below_thresholds",
        ),
        pytest.param(
            {"util": (70.0, 80.0)},
            [["95"], ["95"]],
            [
                Result(
                    state=State.CRIT,
                    summary="Total CPU: 95.00% (warn/crit at 70.00%/80.00%)",
                ),
                Metric("util", 95.0, levels=(70.0, 80.0), boundaries=(0.0, None)),
            ],
            id="crit_breaches_threshold",
        ),
        pytest.param(
            {"util": (80.0, 90.0), "average": 5},
            [["60"], ["80"]],
            [
                Metric("util", 70.0, levels=(80.0, 90.0), boundaries=(0.0, 100.0)),
                Result(state=State.OK, summary="Total CPU (5 min average): 70.00%"),
                Metric("util_average", 70.0, levels=(80.0, 90.0), boundaries=(0.0, None)),
            ],
            id="with_averaging",
        ),
    ],
)
def test_check_hr_cpu(
    params: Mapping[str, Any],
    parsed: StringTable,
    expected_output: CheckResult,
    monkeypatch: pytest.MonkeyPatch,
) -> None:

    value_store: dict[str, Any] = {}
    monkeypatch.setattr(hr_cpu_plugin, "get_value_store", lambda: value_store)

    with time_machine.travel("2026-01-01 00:00:00", tick=False):
        result = list(check_hr_cpu(params, parsed))
    assert result == expected_output
