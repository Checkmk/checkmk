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
from cmk.plugins.innovaphone.agent_based.innovaphone_mem import (
    check_innovaphone_mem,
    discover_innovaphone_mem,
    MemoryUsedPercent,
    parse_innovaphone_mem,
)


@pytest.mark.parametrize(
    "string_table",
    [
        pytest.param([], id="empty payload"),
        pytest.param([[]], id="empty nested payload"),
        pytest.param([["", "not-a-number"]], id="not a number"),
    ],
)
def test_parse_innovaphone_mem_empty_data(string_table: StringTable) -> None:
    assert parse_innovaphone_mem(string_table) is None


def test_parse_innovaphone_mem_success() -> None:
    assert parse_innovaphone_mem([["MEM", "55"]]) == MemoryUsedPercent(55)


def test_discover_innovaphone_mem() -> None:
    section = MemoryUsedPercent(55)
    assert list(discover_innovaphone_mem(section)) == [Service()]


@pytest.mark.parametrize(
    "params, section, expected",
    [
        pytest.param(
            {"levels": (60.0, 70.0)},
            MemoryUsedPercent(55),
            [
                Result(state=State.OK, summary="Current: 55.00%"),
                Metric("mem_used_percent", 55.0, levels=(60.0, 70.0)),
            ],
            id="ok_below_warn_threshold",
        ),
        pytest.param(
            {"levels": (60.0, 70.0)},
            MemoryUsedPercent(65),
            [
                Result(state=State.WARN, summary="Current: 65.00% (warn/crit at 60.00%/70.00%)"),
                Metric("mem_used_percent", 65.0, levels=(60.0, 70.0)),
            ],
            id="warn_above_warn_threshold",
        ),
        pytest.param(
            {"levels": (60.0, 70.0)},
            MemoryUsedPercent(85),
            [
                Result(state=State.CRIT, summary="Current: 85.00% (warn/crit at 60.00%/70.00%)"),
                Metric("mem_used_percent", 85.0, levels=(60.0, 70.0)),
            ],
            id="crit_above_crit_threshold",
        ),
    ],
)
def test_check_innovaphone_mem(
    params: Mapping[str, Any],
    section: MemoryUsedPercent,
    expected: list[Result | Metric],
) -> None:
    assert list(check_innovaphone_mem(params, section)) == expected
