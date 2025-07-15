#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import colorsys
import random
from collections import Counter
from dataclasses import dataclass
from typing import Literal

from cmk.ccc.exceptions import MKGeneralException
from cmk.graphing.v1 import metrics as metrics_api
from cmk.gui.ctx_stack import g
from cmk.gui.htmllib.generator import HTMLWriter
from cmk.gui.i18n import _
from cmk.gui.type_defs import RGBColor
from cmk.gui.utils.html import HTML

# Colors:
#
#                   red
#  magenta                       orange
#            11 12 13 14 15 16
#         46                   21
#         45                   22
#   blue  44                   23  yellow
#         43                   24
#         42                   25
#         41                   26
#            36 35 34 33 32 31
#     cyan                       yellow-green
#                  green
#
# Special colors:
# 51  gray
# 52  brown 1
# 53  brown 2
#
# For a new metric_info you have to choose a color. No more hex-codes are needed!
# Instead you can choose a number of the above color ring and a letter 'a' or 'b
# where 'a' represents the basic color and 'b' is a nuance/shading of the basic color.
# Both number and letter must be declared!
#
# Example:
# "color" : "23/a" (basic color yellow)
# "color" : "23/b" (nuance of color yellow)
#
# As an alternative you can call indexed_color with a color index and the maximum
# number of colors you will need to generate a color. This function tries to return
# high contrast colors for "close" indices, so the colors of idx 1 and idx 2 may
# have stronger contrast than the colors at idx 3 and idx 10.

# retrieve an indexed color.
# param idx: the color index
# param total: the total number of colors needed in one graph.
_COLOR_WHEEL_SIZE = 48


def indexed_color(idx: int, total: int) -> str:
    if total < 1:
        raise MKGeneralException(f"{total=} must be larger than zero")
    if not 0 <= idx <= total:
        raise MKGeneralException(f"{idx=} must be in the range 0 <= idx <= {total=}.")

    if idx < _COLOR_WHEEL_SIZE:
        # use colors from the color wheel if possible
        base_col = (idx % 4) + 1
        tone = ((idx // 4) % 6) + 1
        shade = "a" if idx % 8 < 4 else "b"
        return "%d%d/%s" % (base_col, tone, shade)

    # generate distinct rgb values. these may be ugly ; also, they
    # may overlap with the colors from the wheel
    idx_shifted = idx - _COLOR_WHEEL_SIZE
    total_shifted = total - _COLOR_WHEEL_SIZE

    # 7 possible rgb combinations: # red, green, blue, red+green, red+blue, green+blue, red+green+blue
    rgb_combination = idx_shifted % 7
    red = int(rgb_combination in [0, 3, 4, 6])
    green = int(rgb_combination in [1, 3, 5, 6])
    blue = int(rgb_combination in [2, 4, 5, 6])

    # avoid too dark and too light greys
    if red and green and blue:
        rgb_value_min = 100
        rgb_value_max = 200
    # avoid too dark colors (cannot be distinguished)
    else:
        rgb_value_min = 60
        rgb_value_max = 230

    rgb_value = rgb_value_min + int(
        (rgb_value_max - rgb_value_min) * (1 - idx_shifted / total_shifted)
    )

    return _rgb_color_to_hex_color(red * rgb_value, green * rgb_value, blue * rgb_value)


# TODO: Refactor color stuff to dedicatedclass

# Try to distribute colors in a whay that the psychological
# colors distance is distributed evenly.
_hsv_color_distribution = [
    (0.1, 10.0),  # orange ... red
    (0.2, 10.0),  # orange ... yellow(-greenish)
    (0.3, 5.0),  # green-yellow
    (0.4, 2.0),  # green
    (0.5, 5.0),  # green .... cyan
    (0.6, 20.0),  # cyan ... seablue
    (0.7, 10.0),  # seablue ... dark blue
    (0.8, 20.0),  # dark blue ... violet
    (0.9, 20.0),  # violet .. magenta
    (1.0, 20.0),  # magenta .. red
]

_cmk_color_palette = {
    # do not use:
    #   "0"     : (0.33, 1, 1),  # green
    #   "1"     : (0.167, 1, 1), # yellow
    #   "2"     : (0, 1, 1),     # red
    # red area
    "11": (0.775, 1, 1),
    "12": (0.8, 1, 1),
    "13": (0.83, 1, 1),
    "14": (0.05, 1, 1),
    "15": (0.08, 1, 1),
    "16": (0.105, 1, 1),
    # yellow area
    "21": (0.13, 1, 1),
    "22": (0.14, 1, 1),
    "23": (0.155, 1, 1),
    "24": (0.185, 1, 1),
    "25": (0.21, 1, 1),
    "26": (0.25, 1, 1),
    # green area
    "31": (0.45, 1, 1),
    "32": (0.5, 1, 1),
    "33": (0.515, 1, 1),
    "34": (0.53, 1, 1),
    "35": (0.55, 1, 1),
    "36": (0.57, 1, 1),
    # blue area
    "41": (0.59, 1, 1),
    "42": (0.62, 1, 1),
    "43": (0.66, 1, 1),
    "44": (0.71, 1, 1),
    "45": (0.73, 1, 1),
    "46": (0.75, 1, 1),
    # special colors
    "51": (0, 0, 0.5),  # grey_50
    "52": (0.067, 0.7, 0.5),  # brown 1
    "53": (0.083, 0.8, 0.55),  # brown 2
}


def _rgb_color_to_hex_color(red: int, green: int, blue: int) -> str:
    return f"#{red:02x}{green:02x}{blue:02x}"


def _hex_color_to_rgb_color(color: str) -> tuple[int, int, int]:
    """Convert '#112233' or '#123' to (17, 34, 51)"""
    full_color = color
    if len(full_color) == 4:
        # 3-digit hex codes means that both the values (RR, GG, BB) are the same for each component
        # for instance '#ff00cc' can also be written like '#f0c'
        full_color = "#" + full_color[1] * 2 + full_color[2] * 2 + full_color[3] * 2
    try:
        return int(full_color[1:3], 16), int(full_color[3:5], 16), int(full_color[5:7], 16)
    except Exception:
        raise MKGeneralException(_("Invalid color specification '%s'") % color)


# These colors are also used in the CSS stylesheets, do not change one without changing the other.
MONITORING_STATUS_COLORS = {
    "critical/down": _rgb_color_to_hex_color(255, 50, 50),
    "unknown/unreachable": _rgb_color_to_hex_color(255, 136, 0),
    "warning": _rgb_color_to_hex_color(255, 208, 0),
    "in_downtime": _rgb_color_to_hex_color(60, 194, 255),
    "on_down_host": _rgb_color_to_hex_color(16, 99, 176),
    "ok/up": _rgb_color_to_hex_color(19, 211, 137),
}

scalar_colors = {
    "warn": MONITORING_STATUS_COLORS["warning"],
    "crit": MONITORING_STATUS_COLORS["critical/down"],
}


def get_palette_color_by_index(
    i: int,
    shading: Literal["a", "b"] = "a",
) -> str:
    color_key = sorted(_cmk_color_palette.keys())[i % len(_cmk_color_palette)]
    return f"{color_key}/{shading}"


def get_next_random_palette_color() -> str:
    keys = list(_cmk_color_palette.keys())
    if "random_color_index" in g:
        last_index = g.random_color_index
    else:
        last_index = random.randint(0, len(keys))
    index = (last_index + 1) % len(keys)
    g.random_color_index = index
    return parse_color_into_hexrgb("%s/a" % keys[index])


def get_n_different_colors(n: int) -> list[str]:
    """Return a list of colors that are as different as possible (visually)
    by distributing them on the HSV color wheel."""
    total_weight = sum(x[1] for x in _hsv_color_distribution)

    colors: list[str] = []
    while len(colors) < n:
        weight_index = int(len(colors) * total_weight / n)
        hue = _get_hue_by_weight_index(weight_index)
        colors.append(_hsv_to_hexrgb((hue, 1, 1)))
    return colors


def _get_hue_by_weight_index(weight_index: float) -> float:
    section_begin = 0.0
    for section_end, section_weight in _hsv_color_distribution:
        if weight_index < section_weight:
            section_size = section_end - section_begin
            hue = section_begin + int((weight_index / section_weight) * section_size)
            return hue
        weight_index -= section_weight
        section_begin = section_end
    return 0.0  # Hmmm...


# 23/c -> #ff8040
# #ff8040 -> #ff8040
def parse_color_into_hexrgb(color_string: str) -> str:
    if color_string[0] == "#":
        return color_string

    if "/" in color_string:
        cmk_color_index, color_shading = color_string.split("/")
        hsv = _cmk_color_palette[cmk_color_index]

        # Colors of the yellow ("2") and green ("3") area need to be darkened (in third place of the hsv tuple),
        # colors of the red and blue area need to be brightened (in second place of the hsv tuple).
        # For both shadings we need different factors.
        if color_shading == "b":
            factors = (1.0, 1.0, 0.8) if cmk_color_index[0] in ["2", "3"] else (1.0, 0.6, 1.0)
            hsv = _pointwise_multiplication(hsv, factors)

        color_hexrgb = _hsv_to_hexrgb(hsv)
        return color_hexrgb

    return "#808080"


def _pointwise_multiplication(
    c1: tuple[float, float, float], c2: tuple[float, float, float]
) -> tuple[float, float, float]:
    components = list(x * y for x, y in zip(c1, c2))
    return components[0], components[1], components[2]


def _hsv_to_hexrgb(hsv: tuple[float, float, float]) -> str:
    return render_color(colorsys.hsv_to_rgb(*hsv))


def render_color(color_rgb: RGBColor) -> str:
    return _rgb_color_to_hex_color(
        int(color_rgb[0] * 255),
        int(color_rgb[1] * 255),
        int(color_rgb[2] * 255),
    )


def parse_color(color: str) -> RGBColor:
    """Convert '#ff0080' to (1.5, 0.0, 0.5)"""
    rgb = _hex_color_to_rgb_color(color)
    return rgb[0] / 255.0, rgb[1] / 255.0, rgb[2] / 255.0


def fade_color(rgb, v):
    gray = _rgb_to_gray(rgb)
    if gray > 0.5:
        return darken_color(rgb, v)
    return lighten_color(rgb, v)


def darken_color(rgb, v):
    """Make a color darker. v ranges from 0 (not darker) to 1 (black)"""

    def darken(x, v):
        return x * (1.0 - v)

    return tuple(darken(x, v) for x in rgb)


def lighten_color(rgb, v):
    """Make a color lighter. v ranges from 0 (not lighter) to 1 (white)"""

    def lighten(x, v):
        return x + ((1.0 - x) * v)

    return tuple(lighten(x, v) for x in rgb)


def _rgb_to_gray(rgb):
    r, gr, b = rgb
    return 0.21 * r + 0.72 * gr + 0.07 * b


def mix_colors(a, b):
    return tuple((ca + cb) / 2.0 for (ca, cb) in zip(a, b))


def render_color_icon(color: str) -> HTML:
    return HTMLWriter.render_div(
        "",
        class_="color",
        # NOTE: When we drop support for IE11 we can use #%s4c instead of rgba(...)
        style="background-color: rgba(%d, %d, %d, 0.3); border-color: %s;"
        % (*_hex_color_to_rgb_color(color), color),
    )


def get_gray_tone(color_counter: Counter[Literal["metric", "predictive"]]) -> str:
    color_counter.update({"predictive": 1})
    value = ((color_counter["predictive"] * 15) % 136) + 60
    return _rgb_color_to_hex_color(value, value, value)


@dataclass(frozen=True)
class RGB:
    red: int
    green: int
    blue: int


def color_to_rgb(color: metrics_api.Color) -> RGB:
    match color:
        case metrics_api.Color.LIGHT_RED:
            return RGB(255, 112, 112)
        case metrics_api.Color.RED:
            return RGB(255, 41, 41)
        case metrics_api.Color.DARK_RED:
            return RGB(230, 37, 37)

        case metrics_api.Color.LIGHT_ORANGE:
            return RGB(255, 150, 100)
        case metrics_api.Color.ORANGE:
            return RGB(255, 110, 33)
        case metrics_api.Color.DARK_ORANGE:
            return RGB(204, 88, 25)

        case metrics_api.Color.LIGHT_YELLOW:
            return RGB(255, 255, 120)
        case metrics_api.Color.YELLOW:
            return RGB(245, 245, 50)
        case metrics_api.Color.DARK_YELLOW:
            return RGB(170, 170, 0)

        case metrics_api.Color.LIGHT_GREEN:
            return RGB(165, 255, 85)
        case metrics_api.Color.GREEN:
            return RGB(55, 250, 55)
        case metrics_api.Color.DARK_GREEN:
            return RGB(40, 140, 15)

        case metrics_api.Color.LIGHT_BLUE:
            return RGB(135, 206, 250)
        case metrics_api.Color.BLUE:
            return RGB(30, 144, 255)
        case metrics_api.Color.DARK_BLUE:
            return RGB(24, 115, 204)

        case metrics_api.Color.LIGHT_CYAN:
            return RGB(150, 255, 255)
        case metrics_api.Color.CYAN:
            return RGB(30, 230, 230)
        case metrics_api.Color.DARK_CYAN:
            return RGB(20, 135, 140)

        case metrics_api.Color.LIGHT_PURPLE:
            return RGB(225, 179, 249)
        case metrics_api.Color.PURPLE:
            return RGB(210, 141, 246)
        case metrics_api.Color.DARK_PURPLE:
            return RGB(180, 65, 240)

        case metrics_api.Color.LIGHT_PINK:
            return RGB(255, 160, 240)
        case metrics_api.Color.PINK:
            return RGB(255, 100, 255)
        case metrics_api.Color.DARK_PINK:
            return RGB(210, 20, 190)

        case metrics_api.Color.LIGHT_BROWN:
            return RGB(230, 180, 140)
        case metrics_api.Color.BROWN:
            return RGB(191, 133, 72)
        case metrics_api.Color.DARK_BROWN:
            return RGB(153, 106, 58)

        case metrics_api.Color.LIGHT_GRAY:
            return RGB(200, 200, 200)
        case metrics_api.Color.GRAY:
            return RGB(164, 164, 164)
        case metrics_api.Color.DARK_GRAY:
            return RGB(121, 121, 121)

        case metrics_api.Color.BLACK:
            return RGB(0, 0, 0)
        case metrics_api.Color.WHITE:
            return RGB(255, 255, 255)


def parse_color_from_api(color: metrics_api.Color) -> str:
    rgb = color_to_rgb(color)
    return f"#{rgb.red:02x}{rgb.green:02x}{rgb.blue:02x}"
