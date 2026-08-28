#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

import pytest

from cmk.agent_based.v2 import Metric, Result, Service, State, StringTable
from cmk.legacy_checks import fortisandbox_cpu_util
from cmk.legacy_checks.fortisandbox_cpu_util import (
    check_fortisandbox_cpu_util,
    discover_fortisandbox_cpu_util,
    parse_fortisandbox_cpu_util,
)


@pytest.fixture(name="empty_value_store")
def _empty_value_store(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(fortisandbox_cpu_util, "get_value_store", dict)


@pytest.mark.parametrize(
    "string_table, expected",
    [
        pytest.param([["10"]], 10, id="single-value"),
        pytest.param([], None, id="empty"),
        pytest.param([[]], None, id="empty-row"),
    ],
)
def test_parse_fortisandbox_cpu_util(string_table: StringTable, expected: int | None) -> None:
    assert parse_fortisandbox_cpu_util(string_table) == expected


def test_discover_fortisandbox_cpu_util() -> None:
    assert list(discover_fortisandbox_cpu_util(10)) == [Service()]


@pytest.mark.usefixtures("empty_value_store")
@pytest.mark.parametrize(
    "params, section, expected",
    [
        pytest.param(
            {},
            10,
            [
                Result(state=State.OK, summary="Total CPU: 10.00%"),
                Metric("util", 10.0, boundaries=(0.0, None)),
            ],
            id="no levels",
        ),
        pytest.param(
            {"util": (80.0, 90.0)},
            95,
            [
                Result(state=State.CRIT, summary="Total CPU: 95.00% (warn/crit at 80.00%/90.00%)"),
                Metric("util", 95.0, levels=(80.0, 90.0), boundaries=(0.0, None)),
            ],
            id="crit",
        ),
    ],
)
def test_check_fortisandbox_cpu_util(
    params: Mapping[str, object],
    section: int,
    expected: Sequence[object],
) -> None:
    assert list(check_fortisandbox_cpu_util(params, section)) == expected
