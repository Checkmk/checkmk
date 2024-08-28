#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.ccc.exceptions import MKGeneralException

from cmk.gui.graphing._color import _COLOR_WHEEL_SIZE, _hex_color_to_rgb_color, indexed_color


@pytest.mark.parametrize(
    "hex_color, expected_rgb",
    [
        ("#112233", (17, 34, 51)),
        ("#123", (17, 34, 51)),
    ],
)
def test__hex_color_to_rgb_color(hex_color: str, expected_rgb: tuple[int, int, int]) -> None:
    assert _hex_color_to_rgb_color(hex_color) == expected_rgb


@pytest.mark.parametrize(
    ["idx", "total"],
    [
        (-1, -1),
        (-1, 0),
        (0, 0),
        (1, 0),
    ],
)
def test_indexed_color_raises(idx: int, total: int) -> None:
    with pytest.raises(MKGeneralException):
        indexed_color(idx, total)


@pytest.mark.parametrize(
    "idx",
    range(0, _COLOR_WHEEL_SIZE),
)
def test_indexed_color_uses_color_wheel_first(idx: int) -> None:
    assert "/" in indexed_color(idx, _COLOR_WHEEL_SIZE)


@pytest.mark.parametrize(
    ["idx", "total"],
    [
        (89, 143),
        (55, 55),
        (355, 552),
        (90, 100),
        (67, 89),
        (95, 452),
        (111, 222),
    ],
)
def test_indexed_color_sanity(idx: int, total: int) -> None:
    color = indexed_color(idx, total)
    assert "/" not in color
    r, g, b = _hex_color_to_rgb_color(color)
    if r == g == b:
        assert all(100 <= component <= 200 for component in (r, g, b))
    else:
        assert all(60 <= component <= 230 for component in (r, g, b) if component)
