#!/usr/bin/env python
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
from typing import Dict as _Dict  # pylint: disable=unused-import

import cmk.gui.utils as utils
import cmk.gui.metrics as metrics
from cmk.gui.i18n import _
from cmk.gui.globals import html
from cmk.gui.htmllib import HTML
from cmk.gui.exceptions import MKGeneralException
from cmk.gui.view_utils import get_themed_perfometer_bg_color

from cmk.utils.plugin_loader import load_plugins

#.
#   .--Plugin API----------------------------------------------------------.
#   |           ____  _             _            _    ____ ___             |
#   |          |  _ \| |_   _  __ _(_)_ __      / \  |  _ \_ _|            |
#   |          | |_) | | | | |/ _` | | '_ \    / _ \ | |_) | |             |
#   |          |  __/| | |_| | (_| | | | | |  / ___ \|  __/| |             |
#   |          |_|   |_|\__,_|\__, |_|_| |_| /_/   \_\_|  |___|            |
#   |                         |___/                                        |
#   '----------------------------------------------------------------------'

# TODO: Is this unused?
perfometers = {}  # type: _Dict

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


#helper function for perfometer tables
def render_perfometer_td(perc, color):
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
    return html.render_td('', class_="inner", style=style)


# render the perfometer table
# data is expected to be a list of tuples [(perc, color), (perc2, color2), ...]
def render_perfometer(data):
    tds = HTML().join(render_perfometer_td(percentage, color) for percentage, color in data)
    return html.render_table(html.render_tr(tds))


# Paint linear performeter with one value
def perfometer_linear(perc, color):
    return render_perfometer([(perc, color), (100 - perc, get_themed_perfometer_bg_color())])


# Paint logarithm with base 10, half_value is being
# displayed at 50% of the width
def perfometer_logarithmic(value, half_value, base, color):
    return render_metricometer([
        metrics.MetricometerRendererLogarithmic.get_stack_from_values(value, half_value, base,
                                                                      color)
    ])


# prepare the rows for logarithmic perfometers (left or right)
def calculate_half_row_logarithmic(left_or_right, value, color, half_value, base):
    value = float(value)

    if value == 0.0:
        pos = 0.0
    else:
        half_value = float(half_value)
        h = math.log(half_value, base)  # value to be displayed at 50%
        pos = 25 + 10.0 * (math.log(value, base) - h)
        if pos < 1:
            pos = 1
        if pos > 49:
            pos = 49
    if left_or_right == "right":
        return [(pos, color), (50 - pos, get_themed_perfometer_bg_color())]
    return [(50 - pos, get_themed_perfometer_bg_color()), (pos, color)]


# Dual logarithmic Perf-O-Meter
def perfometer_logarithmic_dual(value_left, color_left, value_right, color_right, half_value, base):
    data = []
    data.extend(calculate_half_row_logarithmic("left", value_left, color_left, half_value, base))
    data.extend(calculate_half_row_logarithmic("right", value_right, color_right, half_value, base))
    return render_perfometer(data)


def perfometer_logarithmic_dual_independent(value_left, color_left, half_value_left, base_left,
                                            value_right, color_right, half_value_right, base_right):
    data = []
    data.extend(
        calculate_half_row_logarithmic("left", value_left, color_left, half_value_left, base_left))
    data.extend(
        calculate_half_row_logarithmic("right", value_right, color_right, half_value_right,
                                       base_right))
    return render_perfometer(data)


#.
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
def render_metricometer(stack):
    if len(stack) not in (1, 2):
        raise MKGeneralException(
            _("Invalid Perf-O-Meter definition %r: only one or two entries are allowed") % stack)
    h = HTML().join(map(render_perfometer, stack))
    if len(stack) == 2:
        h = html.render_div(h, class_="stacked")
    return h


# Load the legacy plugins
utils.load_web_plugins("perfometer", globals())

#.
#   .--Plugins-------------------------------------------------------------.
#   |                   ____  _             _                              |
#   |                  |  _ \| |_   _  __ _(_)_ __  ___                    |
#   |                  | |_) | | | | |/ _` | | '_ \/ __|                   |
#   |                  |  __/| | |_| | (_| | | | | \__ \                   |
#   |                  |_|   |_|\__,_|\__, |_|_| |_|___/                   |
#   |                                 |___/                                |
#   '----------------------------------------------------------------------'

load_plugins(__file__, __package__)
