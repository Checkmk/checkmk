#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"
# mypy: disable-error-code="misc"

from collections.abc import Mapping
from typing import Any

import pytest

from cmk.agent_based.v2 import Metric, Result, Service, State, StringTable
from cmk.plugins.innovaphone.agent_based import innovaphone_cpu as innovaphone_cpu_module
from cmk.plugins.innovaphone.agent_based.innovaphone_cpu import (
    check_innovaphone_cpu,
    discover_innovaphone_cpu,
    parse_innovaphone_cpu,
)

_SECTION: StringTable = [["CPU", "55"]]


def test_parse_innovaphone_cpu_keeps_string_table() -> None:
    assert parse_innovaphone_cpu(_SECTION) == _SECTION


def test_discover_innovaphone_cpu() -> None:
    assert list(discover_innovaphone_cpu(_SECTION)) == [Service()]


@pytest.mark.parametrize(
    "params, section, expected",
    [
        pytest.param(
            {"util": (90.0, 95.0)},
            [["CPU", "55"]],
            [
                Result(state=State.OK, summary="Total CPU: 55.00%"),
                Metric("util", 55.0, levels=(90.0, 95.0), boundaries=(0.0, None)),
            ],
            id="ok state",
        ),
        pytest.param(
            {"util": (90.0, 95.0)},
            [["CPU", "93"]],
            [
                Result(state=State.WARN, summary="Total CPU: 93.00% (warn/crit at 90.00%/95.00%)"),
                Metric("util", 93.0, levels=(90.0, 95.0), boundaries=(0.0, None)),
            ],
            id="warn state",
        ),
        pytest.param(
            {"util": (90.0, 95.0)},
            [["CPU", "97"]],
            [
                Result(state=State.CRIT, summary="Total CPU: 97.00% (warn/crit at 90.00%/95.00%)"),
                Metric("util", 97.0, levels=(90.0, 95.0), boundaries=(0.0, None)),
            ],
            id="crit state",
        ),
        pytest.param(
            {"util": (90.0, 95.0)},
            [["CPU", "not-a-number"]],
            [
                Result(state=State.OK, summary="Total CPU: 0%"),
                Metric("util", 0.0, levels=(90.0, 95.0), boundaries=(0.0, None)),
            ],
            id="unparsable_value_falls_back_to_zero",
        ),
    ],
)
def test_check_innovaphone_cpu(
    params: Mapping[str, Any],
    section: StringTable,
    expected: list[Result | Metric],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(innovaphone_cpu_module, "get_value_store", dict)
    assert list(check_innovaphone_cpu(params, section)) == expected
