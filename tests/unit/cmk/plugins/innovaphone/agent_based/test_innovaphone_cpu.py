#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

from collections.abc import Mapping
from typing import Any

import pytest

from cmk.agent_based.v2 import Metric, Result, Service, State, StringTable
from cmk.plugins.innovaphone.agent_based import innovaphone_cpu as innovaphone_cpu_module
from cmk.plugins.innovaphone.agent_based.innovaphone_cpu import (
    check_innovaphone_cpu,
    discover_innovaphone_cpu,
    parse_innovaphone_cpu,
    Utilization,
)


@pytest.mark.parametrize(
    "string_table",
    [
        pytest.param([], id="empty payload"),
        pytest.param([[]], id="empty nested payload"),
        pytest.param([["", "not-a-number"]], id="not a number"),
    ],
)
def test_parse_innovaphone_cpu_empty_data(string_table: StringTable) -> None:
    assert parse_innovaphone_cpu(string_table) is None


def test_parse_innovaphone_cpu_success() -> None:
    assert parse_innovaphone_cpu([["CPU", "55"]]) == Utilization(55)


def test_discover_innovaphone_cpu() -> None:
    section = Utilization(55)
    assert list(discover_innovaphone_cpu(section)) == [Service()]


@pytest.mark.parametrize(
    "params, section, expected",
    [
        pytest.param(
            {"util": (90.0, 95.0)},
            Utilization(55),
            [
                Result(state=State.OK, summary="Total CPU: 55.00%"),
                Metric("util", 55.0, levels=(90.0, 95.0), boundaries=(0.0, None)),
            ],
            id="ok state",
        ),
        pytest.param(
            {"util": (90.0, 95.0)},
            Utilization(93),
            [
                Result(state=State.WARN, summary="Total CPU: 93.00% (warn/crit at 90.00%/95.00%)"),
                Metric("util", 93.0, levels=(90.0, 95.0), boundaries=(0.0, None)),
            ],
            id="warn state",
        ),
        pytest.param(
            {"util": (90.0, 95.0)},
            Utilization(97),
            [
                Result(state=State.CRIT, summary="Total CPU: 97.00% (warn/crit at 90.00%/95.00%)"),
                Metric("util", 97.0, levels=(90.0, 95.0), boundaries=(0.0, None)),
            ],
            id="crit state",
        ),
    ],
)
def test_check_innovaphone_cpu(  # type: ignore[misc]
    params: Mapping[str, Any],
    section: Utilization,
    expected: list[Result | Metric],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(innovaphone_cpu_module, "get_value_store", dict)
    assert list(check_innovaphone_cpu(params, section)) == expected
