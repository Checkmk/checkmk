#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"
# mypy: disable-error-code="no-untyped-call"

from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from cmk.legacy_checks.sophos_cpu import check_sophos_cpu, discover_sophos_cpu, parse_sophos_cpu


def test_parse_sophos_cpu() -> None:
    assert parse_sophos_cpu([["27"]]) == 27


def test_parse_sophos_cpu_invalid_returns_none() -> None:
    assert parse_sophos_cpu([["bogus"]]) is None


@pytest.mark.parametrize(
    "parsed",
    [
        pytest.param(27, id="with_value"),
        pytest.param(None, id="with_none"),
    ],
)
def test_discover_sophos_cpu_always_yields_single_service(parsed: int | None) -> None:
    assert list(discover_sophos_cpu(parsed)) == [(None, {})]


@pytest.mark.parametrize(
    "params, parsed, expected",
    [
        pytest.param(
            {"cpu_levels": (80.0, 90.0)},
            27,
            (0, "Total CPU: 27.00%", [("util", 27, 80.0, 90.0, 0, 100)]),
            id="ok_below_warn",
        ),
        pytest.param(
            {"cpu_levels": (80.0, 90.0)},
            95,
            (
                2,
                "Total CPU: 95.00% (warn/crit at 80.00%/90.00%)",
                [("util", 95, 80.0, 90.0, 0, 100)],
            ),
            id="crit_above_crit",
        ),
    ],
)
def test_check_sophos_cpu(
    params: Mapping[str, Any],
    parsed: int,
    expected: tuple[int, str, Sequence[tuple[str, int, float, float, int, int]]],
) -> None:
    assert list(check_sophos_cpu(None, params, parsed)) == [expected]
