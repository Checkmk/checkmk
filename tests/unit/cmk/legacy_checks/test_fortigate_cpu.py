#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

import pytest

from cmk.agent_based.v2 import Metric, Result, Service, State, StringTable
from cmk.legacy_checks import fortigate_cpu
from cmk.legacy_checks.fortigate_cpu import (
    check_fortigate_cpu,
    discover_fortigate_cpu,
    parse_fortigate_cpu,
)


@pytest.fixture(name="empty_value_store")
def _empty_value_store(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(fortigate_cpu, "get_value_store", dict)


def test_parse_fortigate_cpu_keeps_stringtable() -> None:
    string_table = [["25"], ["31"]]
    assert parse_fortigate_cpu(string_table) == string_table


def test_parse_fortigate_cpu_empty_returns_none() -> None:
    assert parse_fortigate_cpu([]) is None


def test_discover_fortigate_cpu() -> None:
    assert list(discover_fortigate_cpu([["25"], ["31"]])) == [Service()]


@pytest.mark.usefixtures("empty_value_store")
@pytest.mark.parametrize(
    "params, section, expected",
    [
        pytest.param(
            {"util": (80.0, 90.0)},
            [["25"], ["31"]],
            [
                Result(state=State.OK, summary="Total CPU: 28.00% at 2 CPUs"),
                Metric("util", 28.0, levels=(80.0, 90.0), boundaries=(0.0, None)),
            ],
            id="ok",
        ),
        pytest.param(
            {"util": (80.0, 90.0)},
            [["95"], ["99"]],
            [
                Result(
                    state=State.CRIT,
                    summary="Total CPU: 97.00% (warn/crit at 80.00%/90.00%) at 2 CPUs",
                ),
                Metric("util", 97.0, levels=(80.0, 90.0), boundaries=(0.0, None)),
            ],
            id="crit",
        ),
    ],
)
def test_check_fortigate_cpu(
    params: Mapping[str, object],
    section: StringTable,
    expected: Sequence[object],
) -> None:
    assert list(check_fortigate_cpu(params, section)) == expected
