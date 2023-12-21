#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

import pytest

from cmk.base.legacy_checks.f5_bigip_mem import (
    check_f5_bigip_mem,
    discover_f5_bigip_mem,
    parse_f5_bigip_mem,
)

pytestmark = pytest.mark.checks


@pytest.mark.parametrize(
    "info, result",
    [
        ([["", "", "", ""]], []),
        ([["", 0, "", ""]], []),
        ([[0, "", "", ""]], []),
        ([[0, 0, "", ""]], [("total", {})]),
        ([[1, 0, "", ""]], [("total", {})]),
    ],
)
def test_f5_bigip_mem_discovery(
    info: Sequence[Sequence[str | int]], result: Sequence[object]
) -> None:
    assert list(discover_f5_bigip_mem(parse_f5_bigip_mem(info))) == result


@pytest.mark.parametrize(
    "parsed, item, expected_result",
    [
        (
            {
                "total": (50586898432.0, 13228459584.0),
                "TMM": (20497563648.0, 885875712.0),
            },
            "total",
            (
                0,
                "Usage: 26.15% - 12.3 GiB of 47.1 GiB",
                [("mem_used", 13228459584.0, None, None, 0, 50586898432.0)],
            ),
        ),
        (
            {
                "total": (50586898432.0, 13228459584.0),
                "TMM": (20497563648.0, 885875712.0),
            },
            "TMM",
            (
                0,
                "Usage: 4.32% - 845 MiB of 19.1 GiB",
                [("mem_used", 885875712.0, None, None, 0, 20497563648.0)],
            ),
        ),
    ],
)
def test_f5_bigip_mem_check(
    parsed: Mapping[str, tuple[float, float]], item: str, expected_result: object
) -> None:
    assert check_f5_bigip_mem(item, {}, parsed) == expected_result
