#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.agent_based.v2 import Metric, Result, Service, State, StringTable
from cmk.plugins.innovaphone.agent_based import innovaphone_temp as innovaphone_temp_module
from cmk.plugins.innovaphone.agent_based.innovaphone_temp import (
    Celsius,
    check_innovaphone_temp,
    discover_innovaphone_temp,
    parse_innovaphone_temp,
)
from cmk.plugins.lib.temperature import TempParamType


@pytest.mark.parametrize(
    "string_table",
    [
        pytest.param([], id="empty payload"),
        pytest.param([[]], id="empty nested payload"),
        pytest.param([["", "not-a-number"]], id="not a number"),
    ],
)
def test_parse_innovaphone_temp_empty_data(string_table: StringTable) -> None:
    assert parse_innovaphone_temp(string_table) is None


@pytest.mark.parametrize("temp", [-1, 0, 1])
def test_parse_innovaphone_temp_success(temp: int) -> None:
    assert parse_innovaphone_temp([["TEMP", str(temp)]]) == Celsius(temp)


def test_discover_innovaphone_temp() -> None:
    section = Celsius(30)
    assert list(discover_innovaphone_temp(section)) == [Service(item="Ambient")]


@pytest.mark.parametrize(
    "params, section, expected",
    [
        pytest.param(
            {"levels": (45.0, 50.0)},
            Celsius(30),
            [
                Metric("temp", 30.0, levels=(45.0, 50.0)),
                Result(state=State.OK, summary="Temperature: 30 °C"),
                Result(
                    state=State.OK,
                    notice="Configuration: prefer user levels over device levels (used user levels)",
                ),
            ],
            id="ok state",
        ),
        pytest.param(
            {"levels": (45.0, 50.0)},
            Celsius(47),
            [
                Metric("temp", 47.0, levels=(45.0, 50.0)),
                Result(
                    state=State.WARN,
                    summary="Temperature: 47 °C (warn/crit at 45.0 °C/50.0 °C)",
                ),
                Result(
                    state=State.OK,
                    notice="Configuration: prefer user levels over device levels (used user levels)",
                ),
            ],
            id="warn state",
        ),
        pytest.param(
            {"levels": (45.0, 50.0)},
            Celsius(55),
            [
                Metric("temp", 55.0, levels=(45.0, 50.0)),
                Result(
                    state=State.CRIT,
                    summary="Temperature: 55 °C (warn/crit at 45.0 °C/50.0 °C)",
                ),
                Result(
                    state=State.OK,
                    notice="Configuration: prefer user levels over device levels (used user levels)",
                ),
            ],
            id="crit state",
        ),
    ],
)
def test_check_innovaphone_temp(
    params: TempParamType,
    section: Celsius,
    expected: list[Result | Metric],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(innovaphone_temp_module, "get_value_store", dict)
    assert list(check_innovaphone_temp("Ambient", params, section)) == expected
