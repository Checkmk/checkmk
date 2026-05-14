#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"

from collections.abc import Mapping, Sequence
from typing import Any

import pytest
import time_machine

from cmk.agent_based.v2 import Metric, Result, Service, State, StringTable
from cmk.plugins.avaya.agent_based import avaya_88xx_cpu as avaya_88xx_cpu_module
from cmk.plugins.avaya.agent_based.avaya_88xx_cpu import (
    check_avaya_88xx_cpu,
    discover_avaya_88xx_cpu,
    parse_avaya_88xx_cpu,
)

_SECTION_30: StringTable = [["30"]]
_SECTION_99: StringTable = [["99"]]


def test_discover_avaya_88xx_cpu() -> None:
    assert list(discover_avaya_88xx_cpu(_SECTION_30)) == [Service()]


def test_parse_avaya_88xx_cpu_empty_returns_none() -> None:
    assert parse_avaya_88xx_cpu([]) is None


@pytest.mark.parametrize(
    "params, section, expected",
    [
        pytest.param(
            {"util": (90.0, 95.0)},
            _SECTION_30,
            [
                Result(state=State.OK, summary="Total CPU: 30.00%"),
                Metric("util", 30.0, levels=(90.0, 95.0), boundaries=(0.0, None)),
            ],
            id="ok_below_warn_threshold",
        ),
        pytest.param(
            {"util": (90.0, 95.0)},
            _SECTION_99,
            [
                Result(
                    state=State.CRIT,
                    summary="Total CPU: 99.00% (warn/crit at 90.00%/95.00%)",
                ),
                Metric("util", 99.0, levels=(90.0, 95.0), boundaries=(0.0, None)),
            ],
            id="crit_above_crit_threshold",
        ),
    ],
)
def test_check_avaya_88xx_cpu(
    params: Mapping[str, Any],
    section: StringTable,
    expected: Sequence[Result | Metric],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(avaya_88xx_cpu_module, "get_value_store", dict)
    with time_machine.travel("2026-01-01 00:00:00", tick=False):
        assert list(check_avaya_88xx_cpu(params, section)) == expected
