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
from cmk.plugins.avaya.agent_based import avaya_45xx_cpu as avaya_45xx_cpu_module
from cmk.plugins.avaya.agent_based.avaya_45xx_cpu import (
    check_avaya_45xx_cpu,
    discover_avaya_45xx_cpu,
)

_SECTION_DISCOVERY: StringTable = [["30"], ["80"], ["20"]]
_SECTION_OK: StringTable = [["30"], ["80"]]
_SECTION_CRIT: StringTable = [["99"], ["80"]]


def test_discover_avaya_45xx_cpu() -> None:
    assert list(discover_avaya_45xx_cpu(_SECTION_DISCOVERY)) == [
        Service(item="0"),
        Service(item="1"),
        Service(item="2"),
    ]


@pytest.mark.parametrize(
    "item, params, section, expected",
    [
        pytest.param(
            "0",
            {"levels": (90.0, 95.0)},
            _SECTION_OK,
            [
                Result(state=State.OK, summary="Total CPU: 30.00%"),
                Metric("util", 30.0, levels=(90.0, 95.0), boundaries=(0.0, None)),
            ],
            id="ok_below_warn_threshold",
        ),
        pytest.param(
            "0",
            {"levels": (90.0, 95.0)},
            _SECTION_CRIT,
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
def test_check_avaya_45xx_cpu(
    item: str,
    params: Mapping[str, Any],
    section: StringTable,
    expected: Sequence[Result | Metric],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(avaya_45xx_cpu_module, "get_value_store", dict)
    with time_machine.travel("2026-01-01 00:00:00", tick=False):
        assert list(check_avaya_45xx_cpu(item, params, section)) == expected
