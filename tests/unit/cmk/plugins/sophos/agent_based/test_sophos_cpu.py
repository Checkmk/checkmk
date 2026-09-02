#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

import pytest

from cmk.agent_based.v2 import Metric, Result, Service, State
from cmk.plugins.sophos.agent_based.sophos_cpu import (
    check_sophos_cpu,
    discover_sophos_cpu,
    Params,
    parse_sophos_cpu,
)


def test_parse_sophos_cpu() -> None:
    assert parse_sophos_cpu([["27"]]) == 27


def test_parse_sophos_cpu_invalid_returns_none() -> None:
    assert parse_sophos_cpu([["bogus"]]) is None


def test_discover_sophos_cpu_yields_single_service() -> None:
    assert list(discover_sophos_cpu(27)) == [Service()]


@pytest.mark.parametrize(
    "params, section, expected",
    [
        pytest.param(
            {"cpu_levels": (80.0, 90.0)},
            27,
            [
                Result(state=State.OK, summary="Total CPU: 27.00%"),
                Metric("util", 27.0, levels=(80.0, 90.0), boundaries=(0.0, 100.0)),
            ],
            id="ok_below_warn",
        ),
        pytest.param(
            {"cpu_levels": (80.0, 90.0)},
            95,
            [
                Result(state=State.CRIT, summary="Total CPU: 95.00% (warn/crit at 80.00%/90.00%)"),
                Metric("util", 95.0, levels=(80.0, 90.0), boundaries=(0.0, 100.0)),
            ],
            id="crit_above_crit",
        ),
        pytest.param(
            {},
            27,
            [
                Result(state=State.OK, summary="Total CPU: 27.00%"),
                Metric("util", 27.0, boundaries=(0.0, 100.0)),
            ],
            id="no_levels_configured",
        ),
    ],
)
def test_check_sophos_cpu(
    params: Params,
    section: int,
    expected: Sequence[Result | Metric],
) -> None:
    assert list(check_sophos_cpu(params, section)) == expected
