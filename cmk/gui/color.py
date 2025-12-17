#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import colorsys
import random
from collections import Counter
from dataclasses import dataclass
from enum import Enum
from typing import Literal

from cmk.ccc.exceptions import MKGeneralException
from cmk.graphing.v1 import metrics as metrics_api
from cmk.gui.ctx_stack import g
from cmk.gui.htmllib.generator import HTMLWriter
from cmk.gui.i18n import _
from cmk.gui.type_defs import RGBColor
from cmk.gui.utils.html import HTML
from cmk.inventory_ui import v1_unstable as inventory_ui_api

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


def fade_color(rgb: RGBColor, v: float) -> RGBColor:
    gray = _rgb_to_gray(rgb)
    if gray > 0.5:
        return darken_color(rgb, v)
    return lighten_color(rgb, v)


def darken_color(rgb: RGBColor, v: float) -> RGBColor:
    """Make a color darker. v ranges from 0 (not darker) to 1 (black)"""

    def darken(x: float, v: float) -> float:
        return x * (1.0 - v)

    r, g, b = (darken(x, v) for x in rgb)
    return r, g, b


def lighten_color(rgb: RGBColor, v: float) -> RGBColor:
    """Make a color lighter. v ranges from 0 (not lighter) to 1 (white)"""

    def lighten(x: float, v: float) -> float:
        return x + ((1.0 - x) * v)

    r, g, b = (lighten(x, v) for x in rgb)
    return r, g, b


def _rgb_to_gray(rgb: RGBColor) -> float:
    r, gr, b = rgb
    return 0.21 * r + 0.72 * gr + 0.07 * b


def mix_colors(a: RGBColor, b: RGBColor) -> RGBColor:
    mixed_colors = tuple((ca + cb) / 2.0 for (ca, cb) in zip(a, b))
    return mixed_colors[0], mixed_colors[1], mixed_colors[2]


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


@dataclass(frozen=True, kw_only=True)
class ColorChoice:
    brand: str
    fallback: str


class Color(Enum):
    # light-red.30
    LIGHT_RED = ColorChoice(brand="#f37c7c", fallback="#ff7070")
    # light-red.50
    RED = ColorChoice(brand="#ed3b3b", fallback="#ff2929")
    # light-red.70
    DARK_RED = ColorChoice(brand="#a82a2a", fallback="#e62525")
    # orange.30
    LIGHT_ORANGE = ColorChoice(brand="#ffad54", fallback="#ff9664")
    # orange.50
    ORANGE = ColorChoice(brand="#ff8400", fallback="#ff6e21")
    # orange.70
    DARK_ORANGE = ColorChoice(brand="#b55e00", fallback="#cc5819")
    # yellow.30
    LIGHT_YELLOW = ColorChoice(brand="#ffe456", fallback="#ffff78")
    # yellow.50
    YELLOW = ColorChoice(brand="#ffd703", fallback="#f5f532")
    # yellow.70
    DARK_YELLOW = ColorChoice(brand="#ac7c02", fallback="#aaaa00")
    # corporate-green.30
    LIGHT_GREEN = ColorChoice(brand="#62e0bf", fallback="#a5ff55")
    # corporate-green.50
    GREEN = ColorChoice(brand="#15d1a0", fallback="#37fa37")
    # corporate-green.70
    DARK_GREEN = ColorChoice(brand="#0f9472", fallback="#288c0f")
    # light-blue.30
    LIGHT_BLUE = ColorChoice(brand="#6fc1f7", fallback="#87cefa")
    # light-blue.50
    BLUE = ColorChoice(brand="#28a2f3", fallback="#1e90ff")
    # light-blue.70
    DARK_BLUE = ColorChoice(brand="#1c73ad", fallback="#1873cc")
    # cyan.30
    LIGHT_CYAN = ColorChoice(brand="#68eeee", fallback="#96ffff")
    # cyan.50
    CYAN = ColorChoice(brand="#1ee6e6", fallback="#1ee6e6")
    # cyan.70
    DARK_CYAN = ColorChoice(brand="#17b5b5", fallback="#14878c")
    # purple.30
    LIGHT_PURPLE = ColorChoice(brand="#acaaff", fallback="#e1b3f9")
    # purple.50
    PURPLE = ColorChoice(brand="#8380ff", fallback="#d28df6")
    # purple.70
    DARK_PURPLE = ColorChoice(brand="#5d5bb5", fallback="#b441f0")
    # pink.30
    LIGHT_PINK = ColorChoice(brand="#f9a8e2", fallback="#ffa0f0")
    # pink.50
    PINK = ColorChoice(brand="#ec48b6", fallback="#ff64ff")
    # pink.70
    DARK_PINK = ColorChoice(brand="#be187a", fallback="#d214be")
    # brown.30
    LIGHT_BROWN = ColorChoice(brand="#d4ad84", fallback="#e6b48c")
    # brown.50
    BROWN = ColorChoice(brand="#bf8548", fallback="#bf8548")
    # brown.70
    DARK_BROWN = ColorChoice(brand="#885e33", fallback="#996a3a")
    # mist-grey.30
    LIGHT_GRAY = ColorChoice(brand="#acacac", fallback="#c8c8c8")
    # mist-grey.50
    GRAY = ColorChoice(brand="#8c8c8c", fallback="#a4a4a4")
    # mist-grey.70
    DARK_GRAY = ColorChoice(brand="#5d5d5d", fallback="#797979")

    # conference-grey.100
    BLACK = ColorChoice(brand="#1e262e", fallback="#000000")
    # white.100
    WHITE = ColorChoice(brand="#ffffff", fallback="#ffffff")

    @property
    def brand(self) -> str:
        return self.value.brand

    @property
    def fallback(self) -> str:
        return self.value.fallback


def parse_color_from_api(
    color: metrics_api.Color | inventory_ui_api.BackgroundColor | inventory_ui_api.LabelColor,
) -> Color:
    match color:
        case (
            metrics_api.Color.LIGHT_RED
            | inventory_ui_api.BackgroundColor.LIGHT_RED
            | inventory_ui_api.LabelColor.LIGHT_RED
        ):
            return Color.LIGHT_RED
        case (
            metrics_api.Color.RED
            | inventory_ui_api.BackgroundColor.RED
            | inventory_ui_api.LabelColor.RED
        ):
            return Color.RED
        case (
            metrics_api.Color.DARK_RED
            | inventory_ui_api.BackgroundColor.DARK_RED
            | inventory_ui_api.LabelColor.DARK_RED
        ):
            return Color.DARK_RED

        case (
            metrics_api.Color.LIGHT_ORANGE
            | inventory_ui_api.BackgroundColor.LIGHT_ORANGE
            | inventory_ui_api.LabelColor.LIGHT_ORANGE
        ):
            return Color.LIGHT_ORANGE
        case (
            metrics_api.Color.ORANGE
            | inventory_ui_api.BackgroundColor.ORANGE
            | inventory_ui_api.LabelColor.ORANGE
        ):
            return Color.ORANGE
        case (
            metrics_api.Color.DARK_ORANGE
            | inventory_ui_api.BackgroundColor.DARK_ORANGE
            | inventory_ui_api.LabelColor.DARK_ORANGE
        ):
            return Color.DARK_ORANGE

        case (
            metrics_api.Color.LIGHT_YELLOW
            | inventory_ui_api.BackgroundColor.LIGHT_YELLOW
            | inventory_ui_api.LabelColor.LIGHT_YELLOW
        ):
            return Color.LIGHT_YELLOW
        case (
            metrics_api.Color.YELLOW
            | inventory_ui_api.BackgroundColor.YELLOW
            | inventory_ui_api.LabelColor.YELLOW
        ):
            return Color.YELLOW
        case (
            metrics_api.Color.DARK_YELLOW
            | inventory_ui_api.BackgroundColor.DARK_YELLOW
            | inventory_ui_api.LabelColor.DARK_YELLOW
        ):
            return Color.DARK_YELLOW

        case (
            metrics_api.Color.LIGHT_GREEN
            | inventory_ui_api.BackgroundColor.LIGHT_GREEN
            | inventory_ui_api.LabelColor.LIGHT_GREEN
        ):
            return Color.LIGHT_GREEN
        case (
            metrics_api.Color.GREEN
            | inventory_ui_api.BackgroundColor.GREEN
            | inventory_ui_api.LabelColor.GREEN
        ):
            return Color.GREEN
        case (
            metrics_api.Color.DARK_GREEN
            | inventory_ui_api.BackgroundColor.DARK_GREEN
            | inventory_ui_api.LabelColor.DARK_GREEN
        ):
            return Color.DARK_GREEN

        case (
            metrics_api.Color.LIGHT_BLUE
            | inventory_ui_api.BackgroundColor.LIGHT_BLUE
            | inventory_ui_api.LabelColor.LIGHT_BLUE
        ):
            return Color.LIGHT_BLUE
        case (
            metrics_api.Color.BLUE
            | inventory_ui_api.BackgroundColor.BLUE
            | inventory_ui_api.LabelColor.BLUE
        ):
            return Color.BLUE
        case (
            metrics_api.Color.DARK_BLUE
            | inventory_ui_api.BackgroundColor.DARK_BLUE
            | inventory_ui_api.LabelColor.DARK_BLUE
        ):
            return Color.DARK_BLUE

        case (
            metrics_api.Color.LIGHT_CYAN
            | inventory_ui_api.BackgroundColor.LIGHT_CYAN
            | inventory_ui_api.LabelColor.LIGHT_CYAN
        ):
            return Color.LIGHT_CYAN
        case (
            metrics_api.Color.CYAN
            | inventory_ui_api.BackgroundColor.CYAN
            | inventory_ui_api.LabelColor.CYAN
        ):
            return Color.CYAN
        case (
            metrics_api.Color.DARK_CYAN
            | inventory_ui_api.BackgroundColor.DARK_CYAN
            | inventory_ui_api.LabelColor.DARK_CYAN
        ):
            return Color.DARK_CYAN

        case (
            metrics_api.Color.LIGHT_PURPLE
            | inventory_ui_api.BackgroundColor.LIGHT_PURPLE
            | inventory_ui_api.LabelColor.LIGHT_PURPLE
        ):
            return Color.LIGHT_PURPLE
        case (
            metrics_api.Color.PURPLE
            | inventory_ui_api.BackgroundColor.PURPLE
            | inventory_ui_api.LabelColor.PURPLE
        ):
            return Color.PURPLE
        case (
            metrics_api.Color.DARK_PURPLE
            | inventory_ui_api.BackgroundColor.DARK_PURPLE
            | inventory_ui_api.LabelColor.DARK_PURPLE
        ):
            return Color.DARK_PURPLE

        case (
            metrics_api.Color.LIGHT_PINK
            | inventory_ui_api.BackgroundColor.LIGHT_PINK
            | inventory_ui_api.LabelColor.LIGHT_PINK
        ):
            return Color.LIGHT_PINK
        case (
            metrics_api.Color.PINK
            | inventory_ui_api.BackgroundColor.PINK
            | inventory_ui_api.LabelColor.PINK
        ):
            return Color.PINK
        case (
            metrics_api.Color.DARK_PINK
            | inventory_ui_api.BackgroundColor.DARK_PINK
            | inventory_ui_api.LabelColor.DARK_PINK
        ):
            return Color.DARK_PINK

        case (
            metrics_api.Color.LIGHT_BROWN
            | inventory_ui_api.BackgroundColor.LIGHT_BROWN
            | inventory_ui_api.LabelColor.LIGHT_BROWN
        ):
            return Color.LIGHT_BROWN
        case (
            metrics_api.Color.BROWN
            | inventory_ui_api.BackgroundColor.BROWN
            | inventory_ui_api.LabelColor.BROWN
        ):
            return Color.BROWN
        case (
            metrics_api.Color.DARK_BROWN
            | inventory_ui_api.BackgroundColor.DARK_BROWN
            | inventory_ui_api.LabelColor.DARK_BROWN
        ):
            return Color.DARK_BROWN

        case (
            metrics_api.Color.LIGHT_GRAY
            | inventory_ui_api.BackgroundColor.LIGHT_GRAY
            | inventory_ui_api.LabelColor.LIGHT_GRAY
        ):
            return Color.LIGHT_GRAY
        case (
            metrics_api.Color.GRAY
            | inventory_ui_api.BackgroundColor.GRAY
            | inventory_ui_api.LabelColor.GRAY
        ):
            return Color.GRAY
        case (
            metrics_api.Color.DARK_GRAY
            | inventory_ui_api.BackgroundColor.DARK_GRAY
            | inventory_ui_api.LabelColor.DARK_GRAY
        ):
            return Color.DARK_GRAY

        case (
            metrics_api.Color.BLACK
            | inventory_ui_api.BackgroundColor.BLACK
            | inventory_ui_api.LabelColor.BLACK
        ):
            return Color.BLACK
        case (
            metrics_api.Color.WHITE
            | inventory_ui_api.BackgroundColor.WHITE
            | inventory_ui_api.LabelColor.WHITE
        ):
            return Color.WHITE
    raise NotImplementedError(color)
