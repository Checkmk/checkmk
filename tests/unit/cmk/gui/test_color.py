#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

import pytest

from cmk.ccc.exceptions import MKGeneralException
from cmk.graphing.v1 import metrics as metrics_api
from cmk.gui.color import (
    _COLOR_WHEEL_SIZE,
    _hex_color_to_rgb_color,
    indexed_color,
    parse_color_from_api,
)
from cmk.inventory_ui import v1_unstable as inventory_ui_api


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


@pytest.mark.parametrize(
    "colors_from_api, expected_hex_code_brand, expected_hex_code_fallback",
    [
        pytest.param(
            [
                metrics_api.Color.LIGHT_RED,
                inventory_ui_api.BackgroundColor.LIGHT_RED,
                inventory_ui_api.LabelColor.LIGHT_RED,
            ],
            "#f37c7c",
            "#ff7070",
            id="LIGHT_RED",
        ),
        pytest.param(
            [
                metrics_api.Color.RED,
                inventory_ui_api.BackgroundColor.RED,
                inventory_ui_api.LabelColor.RED,
            ],
            "#ed3b3b",
            "#ff2929",
            id="RED",
        ),
        pytest.param(
            [
                metrics_api.Color.DARK_RED,
                inventory_ui_api.BackgroundColor.DARK_RED,
                inventory_ui_api.LabelColor.DARK_RED,
            ],
            "#a82a2a",
            "#e62525",
            id="DARK_RED",
        ),
        pytest.param(
            [
                metrics_api.Color.LIGHT_ORANGE,
                inventory_ui_api.BackgroundColor.LIGHT_ORANGE,
                inventory_ui_api.LabelColor.LIGHT_ORANGE,
            ],
            "#ffad54",
            "#ff9664",
            id="LIGHT_ORANGE",
        ),
        pytest.param(
            [
                metrics_api.Color.ORANGE,
                inventory_ui_api.BackgroundColor.ORANGE,
                inventory_ui_api.LabelColor.ORANGE,
            ],
            "#ff8400",
            "#ff6e21",
            id="ORANGE",
        ),
        pytest.param(
            [
                metrics_api.Color.DARK_ORANGE,
                inventory_ui_api.BackgroundColor.DARK_ORANGE,
                inventory_ui_api.LabelColor.DARK_ORANGE,
            ],
            "#b55e00",
            "#cc5819",
            id="DARK_ORANGE",
        ),
        pytest.param(
            [
                metrics_api.Color.LIGHT_YELLOW,
                inventory_ui_api.BackgroundColor.LIGHT_YELLOW,
                inventory_ui_api.LabelColor.LIGHT_YELLOW,
            ],
            "#ffe456",
            "#ffff78",
            id="LIGHT_YELLOW",
        ),
        pytest.param(
            [
                metrics_api.Color.YELLOW,
                inventory_ui_api.BackgroundColor.YELLOW,
                inventory_ui_api.LabelColor.YELLOW,
            ],
            "#ffd703",
            "#f5f532",
            id="YELLOW",
        ),
        pytest.param(
            [
                metrics_api.Color.DARK_YELLOW,
                inventory_ui_api.BackgroundColor.DARK_YELLOW,
                inventory_ui_api.LabelColor.DARK_YELLOW,
            ],
            "#ac7c02",
            "#aaaa00",
            id="DARK_YELLOW",
        ),
        pytest.param(
            [
                metrics_api.Color.LIGHT_GREEN,
                inventory_ui_api.BackgroundColor.LIGHT_GREEN,
                inventory_ui_api.LabelColor.LIGHT_GREEN,
            ],
            "#62e0bf",
            "#a5ff55",
            id="LIGHT_GREEN",
        ),
        pytest.param(
            [
                metrics_api.Color.GREEN,
                inventory_ui_api.BackgroundColor.GREEN,
                inventory_ui_api.LabelColor.GREEN,
            ],
            "#15d1a0",
            "#37fa37",
            id="GREEN",
        ),
        pytest.param(
            [
                metrics_api.Color.DARK_GREEN,
                inventory_ui_api.BackgroundColor.DARK_GREEN,
                inventory_ui_api.LabelColor.DARK_GREEN,
            ],
            "#0f9472",
            "#288c0f",
            id="DARK_GREEN",
        ),
        pytest.param(
            [
                metrics_api.Color.LIGHT_BLUE,
                inventory_ui_api.BackgroundColor.LIGHT_BLUE,
                inventory_ui_api.LabelColor.LIGHT_BLUE,
            ],
            "#6fc1f7",
            "#87cefa",
            id="LIGHT_BLUE",
        ),
        pytest.param(
            [
                metrics_api.Color.BLUE,
                inventory_ui_api.BackgroundColor.BLUE,
                inventory_ui_api.LabelColor.BLUE,
            ],
            "#28a2f3",
            "#1e90ff",
            id="BLUE",
        ),
        pytest.param(
            [
                metrics_api.Color.DARK_BLUE,
                inventory_ui_api.BackgroundColor.DARK_BLUE,
                inventory_ui_api.LabelColor.DARK_BLUE,
            ],
            "#1c73ad",
            "#1873cc",
            id="DARK_BLUE",
        ),
        pytest.param(
            [
                metrics_api.Color.LIGHT_CYAN,
                inventory_ui_api.BackgroundColor.LIGHT_CYAN,
                inventory_ui_api.LabelColor.LIGHT_CYAN,
            ],
            "#68eeee",
            "#96ffff",
            id="LIGHT_CYAN",
        ),
        pytest.param(
            [
                metrics_api.Color.CYAN,
                inventory_ui_api.BackgroundColor.CYAN,
                inventory_ui_api.LabelColor.CYAN,
            ],
            "#1ee6e6",
            "#1ee6e6",
            id="CYAN",
        ),
        pytest.param(
            [
                metrics_api.Color.DARK_CYAN,
                inventory_ui_api.BackgroundColor.DARK_CYAN,
                inventory_ui_api.LabelColor.DARK_CYAN,
            ],
            "#17b5b5",
            "#14878c",
            id="DARK_CYAN",
        ),
        pytest.param(
            [
                metrics_api.Color.LIGHT_PURPLE,
                inventory_ui_api.BackgroundColor.LIGHT_PURPLE,
                inventory_ui_api.LabelColor.LIGHT_PURPLE,
            ],
            "#acaaff",
            "#e1b3f9",
            id="LIGHT_PURPLE",
        ),
        pytest.param(
            [
                metrics_api.Color.PURPLE,
                inventory_ui_api.BackgroundColor.PURPLE,
                inventory_ui_api.LabelColor.PURPLE,
            ],
            "#8380ff",
            "#d28df6",
            id="PURPLE",
        ),
        pytest.param(
            [
                metrics_api.Color.DARK_PURPLE,
                inventory_ui_api.BackgroundColor.DARK_PURPLE,
                inventory_ui_api.LabelColor.DARK_PURPLE,
            ],
            "#5d5bb5",
            "#b441f0",
            id="DARK_PURPLE",
        ),
        pytest.param(
            [
                metrics_api.Color.LIGHT_PINK,
                inventory_ui_api.BackgroundColor.LIGHT_PINK,
                inventory_ui_api.LabelColor.LIGHT_PINK,
            ],
            "#f9a8e2",
            "#ffa0f0",
            id="LIGHT_PINK",
        ),
        pytest.param(
            [
                metrics_api.Color.PINK,
                inventory_ui_api.BackgroundColor.PINK,
                inventory_ui_api.LabelColor.PINK,
            ],
            "#ec48b6",
            "#ff64ff",
            id="PINK",
        ),
        pytest.param(
            [
                metrics_api.Color.DARK_PINK,
                inventory_ui_api.BackgroundColor.DARK_PINK,
                inventory_ui_api.LabelColor.DARK_PINK,
            ],
            "#be187a",
            "#d214be",
            id="DARK_PINK",
        ),
        pytest.param(
            [
                metrics_api.Color.LIGHT_BROWN,
                inventory_ui_api.BackgroundColor.LIGHT_BROWN,
                inventory_ui_api.LabelColor.LIGHT_BROWN,
            ],
            "#d4ad84",
            "#e6b48c",
            id="LIGHT_BROWN",
        ),
        pytest.param(
            [
                metrics_api.Color.BROWN,
                inventory_ui_api.BackgroundColor.BROWN,
                inventory_ui_api.LabelColor.BROWN,
            ],
            "#bf8548",
            "#bf8548",
            id="BROWN",
        ),
        pytest.param(
            [
                metrics_api.Color.DARK_BROWN,
                inventory_ui_api.BackgroundColor.DARK_BROWN,
                inventory_ui_api.LabelColor.DARK_BROWN,
            ],
            "#885e33",
            "#996a3a",
            id="DARK_BROWN",
        ),
        pytest.param(
            [
                metrics_api.Color.LIGHT_GRAY,
                inventory_ui_api.BackgroundColor.LIGHT_GRAY,
                inventory_ui_api.LabelColor.LIGHT_GRAY,
            ],
            "#acacac",
            "#c8c8c8",
            id="LIGHT_GRAY",
        ),
        pytest.param(
            [
                metrics_api.Color.GRAY,
                inventory_ui_api.BackgroundColor.GRAY,
                inventory_ui_api.LabelColor.GRAY,
            ],
            "#8c8c8c",
            "#a4a4a4",
            id="GRAY",
        ),
        pytest.param(
            [
                metrics_api.Color.DARK_GRAY,
                inventory_ui_api.BackgroundColor.DARK_GRAY,
                inventory_ui_api.LabelColor.DARK_GRAY,
            ],
            "#5d5d5d",
            "#797979",
            id="DARK_GRAY",
        ),
        pytest.param(
            [
                metrics_api.Color.BLACK,
                inventory_ui_api.BackgroundColor.BLACK,
                inventory_ui_api.LabelColor.BLACK,
            ],
            "#1e262e",
            "#000000",
            id="BLACK",
        ),
        pytest.param(
            [
                metrics_api.Color.WHITE,
                inventory_ui_api.BackgroundColor.WHITE,
                inventory_ui_api.LabelColor.WHITE,
            ],
            "#ffffff",
            "#ffffff",
            id="WHITE",
        ),
    ],
)
def test_color(
    colors_from_api: Sequence[
        metrics_api.Color | inventory_ui_api.BackgroundColor | inventory_ui_api.LabelColor
    ],
    expected_hex_code_brand: str,
    expected_hex_code_fallback: str,
) -> None:
    for color_from_api in colors_from_api:
        assert parse_color_from_api(color_from_api).brand == expected_hex_code_brand
        assert parse_color_from_api(color_from_api).fallback == expected_hex_code_fallback
