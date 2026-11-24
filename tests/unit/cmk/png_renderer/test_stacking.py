#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

from cmk.png_renderer import Area, area_bottoms, Stack


def _stack(*tops: Sequence[float | None]) -> Stack:
    return Stack(areas=[Area(color="#000000", top=top) for top in tops])


def test_a_stack_without_areas_has_no_bottoms() -> None:
    assert area_bottoms(_stack(), 3) == []


def test_each_area_starts_on_the_top_of_the_area_below() -> None:
    assert area_bottoms(_stack([1.0, 2.0], [11.0, 22.0], [111.0, 222.0]), 2) == [
        [0.0, 0.0],
        [1.0, 2.0],
        [11.0, 22.0],
    ]


def test_an_area_above_a_gap_starts_at_the_bottom_of_the_gap() -> None:
    assert area_bottoms(_stack([5.0, 5.0, 5.0], [6.0, None, 7.0], [16.0, 17.0, 18.0]), 3)[2] == [
        6.0,
        5.0,
        7.0,
    ]
