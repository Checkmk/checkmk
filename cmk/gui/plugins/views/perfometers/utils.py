#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# TODO: Umbau: alle Funktionen perfometer_.. geben eine logische Struktur
# zurück.
# perfometer_td() -> perfometer_segment() ergibt (breite_in_proz, farbe)
# Ein perfometer ist eine Liste von Listen.
# [ [segment, segment, segment], [segment, segment] ] --> horizontal gespaltet.
# Darin die vertikalen Balken.

import math
from typing import Callable
from typing import Dict as _Dict
from typing import List, Literal, Optional, Tuple

import cmk.gui.metrics as metrics
from cmk.gui.exceptions import MKGeneralException
from cmk.gui.htmllib.generator import HTMLWriter
from cmk.gui.i18n import _
from cmk.gui.type_defs import Perfdata, Row
from cmk.gui.utils.html import HTML
from cmk.gui.view_utils import get_themed_perfometer_bg_color

PerfometerData = List[Tuple[float, str]]

# .
#   .--Plugin API----------------------------------------------------------.
#   |           ____  _             _            _    ____ ___             |
#   |          |  _ \| |_   _  __ _(_)_ __      / \  |  _ \_ _|            |
#   |          | |_) | | | | |/ _` | | '_ \    / _ \ | |_) | |             |
#   |          |  __/| | |_| | (_| | | | | |  / ___ \|  __/| |             |
#   |          |_|   |_|\__,_|\__, |_|_| |_| /_/   \_\_|  |___|            |
#   |                         |___/                                        |
#   '----------------------------------------------------------------------'

LegacyPerfometerResult = Optional[Tuple[str, HTML]]

# "Registry" for old perfometers. There are still some left. See:
# cmk/gui/plugins/views/perfometers/check_mk.py
perfometers: _Dict[str, Callable[[Row, str, Perfdata], LegacyPerfometerResult]] = {}

#   .--Old Style-----------------------------------------------------------.
#   |                ___  _     _   ____  _         _                      |
#   |               / _ \| | __| | / ___|| |_ _   _| | ___                 |
#   |              | | | | |/ _` | \___ \| __| | | | |/ _ \                |
#   |              | |_| | | (_| |  ___) | |_| |_| | |  __/                |
#   |               \___/|_|\__,_| |____/ \__|\__, |_|\___|                |
#   |                                         |___/                        |
#   +----------------------------------------------------------------------+
#   |  Perf-O-Meter helper functions for old classical Perf-O-Meters.      |
#   '----------------------------------------------------------------------'


# helper function for perfometer tables
def render_perfometer_td(perc: float, color: str) -> HTML:
    # the hex color can have additional information about opacity
    # internet explorer has problems with the format of rgba, e.g.: #aaaaaa4d
    # the solution is to set the background-color value to rgb ('#aaaaaa')
    # and use the css opacity for the opacity hex value in float '4d' -> 0.3
    opacity = None
    if len(color) == 9:
        opacity = int(color[7:], 16) / 255.0
        color = color[:7]

    style = ["width: %d%%;" % int(float(perc)), "background-color: %s" % color]
    if opacity is not None:
        style += ["opacity: %s" % opacity]
    return HTMLWriter.render_td("", class_="inner", style=style)


# render the perfometer table
# data is expected to be a list of tuples [(perc, color), (perc2, color2), ...]
def render_perfometer(data: PerfometerData) -> HTML:
    tds = HTML().join(render_perfometer_td(percentage, color) for percentage, color in data)
    return HTMLWriter.render_table(HTMLWriter.render_tr(tds))


# Paint linear performeter with one value
def perfometer_linear(perc: float, color: str) -> HTML:
    return render_perfometer([(perc, color), (100 - perc, get_themed_perfometer_bg_color())])


# Paint logarithm with base 10, half_value is being
# displayed at 50% of the width
def perfometer_logarithmic(value: float, half_value: float, base: float, color: str) -> HTML:
    return render_metricometer(
        [
            metrics.MetricometerRendererLogarithmic.get_stack_from_values(
                value, half_value, base, color
            )
        ]
    )


# prepare the rows for logarithmic perfometers (left or right)
def calculate_half_row_logarithmic(
    left_or_right: Literal["left", "right"],
    value: float,
    color: str,
    half_value: float,
    base: float,
) -> PerfometerData:
    value = float(value)

    if value == 0.0:
        pos = 0.0
    else:
        half_value = float(half_value)
        h = math.log(half_value, base)  # value to be displayed at 50%
        pos = 25 + 10.0 * (math.log(value, base) - h)
        pos = min(max(1, pos), 49)
    if left_or_right == "right":
        return [(pos, color), (50 - pos, get_themed_perfometer_bg_color())]
    return [(50 - pos, get_themed_perfometer_bg_color()), (pos, color)]


# Dual logarithmic Perf-O-Meter
def perfometer_logarithmic_dual(
    value_left: float,
    color_left: str,
    value_right: float,
    color_right: str,
    half_value: float,
    base: float,
) -> HTML:
    data: PerfometerData = []
    data.extend(calculate_half_row_logarithmic("left", value_left, color_left, half_value, base))
    data.extend(calculate_half_row_logarithmic("right", value_right, color_right, half_value, base))
    return render_perfometer(data)


def perfometer_logarithmic_dual_independent(
    value_left: float,
    color_left: str,
    half_value_left: float,
    base_left: float,
    value_right: float,
    color_right: str,
    half_value_right: float,
    base_right: float,
) -> HTML:
    data: PerfometerData = []
    data.extend(
        calculate_half_row_logarithmic("left", value_left, color_left, half_value_left, base_left)
    )
    data.extend(
        calculate_half_row_logarithmic(
            "right", value_right, color_right, half_value_right, base_right
        )
    )
    return render_perfometer(data)


# .
#   .--New Style--(Metric-O-Meters)----------------------------------------.
#   |            _   _                 ____  _         _                   |
#   |           | \ | | _____      __ / ___|| |_ _   _| | ___              |
#   |           |  \| |/ _ \ \ /\ / / \___ \| __| | | | |/ _ \             |
#   |           | |\  |  __/\ V  V /   ___) | |_| |_| | |  __/             |
#   |           |_| \_|\___| \_/\_/   |____/ \__|\__, |_|\___|             |
#   |                                            |___/                     |
#   +----------------------------------------------------------------------+
#   |  Perf-O-Meters created by new metrics system                         |
#   '----------------------------------------------------------------------'


# Create HTML representation of Perf-O-Meter
def render_metricometer(stack) -> HTML:
    if len(stack) not in (1, 2):
        raise MKGeneralException(
            _("Invalid Perf-O-Meter definition %r: only one or two entries are allowed") % stack
        )
    h = HTML().join(map(render_perfometer, stack))
    if len(stack) == 2:
        h = HTMLWriter.render_div(h, class_="stacked")
    return h
