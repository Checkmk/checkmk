#!/usr/bin/env python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# The official homepage is at http://mathias-kettner.de/check_mk.
#
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.
"""Module to hold shared code for main module internals and the plugins"""
from __future__ import division

from collections import OrderedDict
import colorsys
import random
import shlex

import cmk.utils.regex

import cmk.gui.config as config
from cmk.gui.log import logger
from cmk.gui.i18n import _
from cmk.gui.globals import g, html
from cmk.gui.exceptions import MKGeneralException
from cmk.utils.memoize import MemoizeCache


class AutomaticDict(OrderedDict):
    """Dictionary class with the ability of appending items like provided
    by a list."""
    def __init__(self, list_identifier=None, start_index=None):
        OrderedDict.__init__(self)
        self._list_identifier = list_identifier or "item"
        self._item_index = start_index or 0

    def append(self, item):
        self["%s_%i" % (self._list_identifier, self._item_index)] = item
        self._item_index += 1


# TODO: Refactor to plugin_registry structures
unit_info = {}
metric_info = {}
check_metrics = {}
perfometer_info = []
# _AutomaticDict is used here to provide some list methods.
# This is needed to maintain backwards-compatibility.
graph_info = AutomaticDict("manual_graph_template")

scalar_colors = {
    "warn": "#ffff00",
    "crit": "#ff0000",
}

#.
#   .--Constants-----------------------------------------------------------.
#   |              ____                _              _                    |
#   |             / ___|___  _ __  ___| |_ __ _ _ __ | |_ ___              |
#   |            | |   / _ \| '_ \/ __| __/ _` | '_ \| __/ __|             |
#   |            | |__| (_) | | | \__ \ || (_| | | | | |_\__ \             |
#   |             \____\___/|_| |_|___/\__\__,_|_| |_|\__|___/             |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |  Various constants to be used by the declarations of the plugins.    |
#   '----------------------------------------------------------------------'
# TODO: Refactor to some namespace object

KB = 1024
MB = KB * 1024
GB = MB * 1024
TB = GB * 1024
PB = TB * 1024

m = 0.001
K = 1000
M = K * 1000
G = M * 1000
T = G * 1000
P = T * 1000

scale_symbols = {
    m: "m",
    1: "",
    KB: "k",
    MB: "M",
    GB: "G",
    TB: "T",
    PB: "P",
    K: "k",
    M: "M",
    G: "G",
    T: "T",
    P: "P",
}

MAX_CORES = 128

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


def indexed_color(idx, total):
    if idx < _COLOR_WHEEL_SIZE:
        # use colors from the color wheel if possible
        base_col = (idx % 4) + 1
        tone = ((idx // 4) % 6) + 1
        if idx % 8 < 4:
            shade = "a"
        else:
            shade = "b"
        return "%d%d/%s" % (base_col, tone, shade)
    else:
        # generate distinct rgb values. these may be ugly ; also, they
        # may overlap with the colors from the wheel
        idx = idx - _COLOR_WHEEL_SIZE
        base_color = idx % 7  # red, green, blue, red+green, red+blue,
        # green+blue, red+green+blue
        delta = int(255.0 / ((total - _COLOR_WHEEL_SIZE) / 7))
        offset = int(255 - (delta * ((idx / 7.0) + 1)))

        red = int(base_color in [0, 3, 4, 6])
        green = int(base_color in [1, 3, 5, 6])
        blue = int(base_color in [2, 4, 5, 6])
        return "#%02x%02x%02x" % (red * offset, green * offset, blue * offset)


def parse_perf_values(data_str):
    "convert perf str into a tuple with values"
    varname, values = data_str.split("=", 1)
    varname = cmk.utils.pnp_cleanup(varname.replace("\"", "").replace("\'", ""))

    value_parts = values.split(";")
    while len(value_parts) < 5:
        value_parts.append(None)

    return varname, value_parts[0], value_parts[1:]


def split_unit(value_text):
    "separate value from unit"

    if not value_text.strip():
        return None, None

    def digit_unit_split(value_text):
        for i, char in enumerate(value_text):
            if char not in '0123456789.,-':
                return i
        return len(value_text)

    cut_unit = digit_unit_split(value_text)

    unit_name = value_text[cut_unit:]
    if value_text[:cut_unit]:
        return _float_or_int(value_text[:cut_unit]), unit_name

    return None, unit_name


def parse_perf_data(perf_data_string, check_command=None):
    """ Convert perf_data_string into perf_data, extract check_command

This methods must not return None or anything else. It must strictly
return a tuple of perf_data list and the check_command. In case of
errors during parsing it returns an empty list for the perf_data.
"""
    # Strip away arguments like in "check_http!-H checkmk.com"
    if hasattr(check_command, 'split'):
        check_command = check_command.split("!")[0]

    # Split the perf data string into parts. Preserve quoted strings!
    parts = _split_perf_data(perf_data_string)

    if not parts:
        return [], check_command

    # Try if check command is appended to performance data
    # in a PNP like style
    if parts[-1].startswith("[") and parts[-1].endswith("]"):
        check_command = parts[-1][1:-1]
        del parts[-1]

    # Parse performance data, at least try
    perf_data = []

    for part in parts:
        try:
            varname, value_text, value_parts = parse_perf_values(part)

            value, unit_name = split_unit(value_text)
            if value is None:
                continue  # ignore useless empty variable

            perf_data_tuple = (varname, value, unit_name) + tuple(map(_float_or_int, value_parts))
            perf_data.append(perf_data_tuple)
        except Exception as exc:
            logger.exception("Failed to parse perfdata '%s'", perf_data_string)
            if config.debug:
                raise exc

    return perf_data, check_command


def _float_or_int(val):
    """"45.0" -> 45.0, "45" -> 45"""
    if val is None:
        return None

    try:
        return int(val)
    except ValueError:
        try:
            return float(val)
        except ValueError:
            return None


def _split_perf_data(perf_data_string):
    "Split the perf data string into parts. Preserve quoted strings!"
    try:  # python3
        return shlex.split(perf_data_string)
    except UnicodeEncodeError:
        # In python 2 shlex.split can not deal with unicode strings. But we always
        # have unicode strings. So encode and decode again.
        return [s.decode('utf-8') for s in shlex.split(perf_data_string.encode('utf-8'))]


def perfvar_translation(perfvar_name, check_command):
    """Get translation info for one performance var."""
    cm = check_metrics.get(check_command, {})
    translation_entry = {}  # Default: no translation necessary

    if perfvar_name in cm:
        translation_entry = cm[perfvar_name]
    else:
        for orig_varname, te in cm.items():
            if orig_varname[0] == "~" and cmk.utils.regex.regex(
                    orig_varname[1:]).match(perfvar_name):  # Regex entry
                translation_entry = te
                break

    return {
        "name": translation_entry.get("name", perfvar_name),
        "scale": translation_entry.get("scale", 1.0),
        "auto_graph": translation_entry.get("auto_graph", True),
    }


def scalar_bounds(perfvar_bounds, scale):
    """rescale "warn, crit, min, max" PERFVAR_BOUNDS values

    Return "None" entries if no performance data and hence no scalars are available
    """

    scalars = {}
    for name, value in zip(("warn", "crit", "min", "max"), perfvar_bounds):
        if value is not None:
            scalars[name] = float(value) * scale
    return scalars


def normalize_perf_data(perf_data, check_command):
    translation_entry = perfvar_translation(perf_data[0], check_command)

    new_entry = {
        "orig_name": perf_data[0],
        "value": perf_data[1] * translation_entry["scale"],
        "scalar": scalar_bounds(perf_data[3:], translation_entry["scale"]),
        "scale": translation_entry["scale"],  # needed for graph recipes
        # Do not create graphs for ungraphed metrics if listed here
        "auto_graph": translation_entry["auto_graph"],
    }

    return translation_entry["name"], new_entry


def get_metric_info(metric_name, color_index):

    if metric_name not in metric_info:
        color_index += 1
        palette_color = get_palette_color_by_index(color_index)
        mi = {
            "title": metric_name.title(),
            "unit": "",
            "color": parse_color_into_hexrgb(palette_color),
        }
    else:
        mi = metric_info[metric_name].copy()
        mi["color"] = parse_color_into_hexrgb(mi["color"])

    return mi, color_index


def translate_metrics(perf_data, check_command):
    """Convert Ascii-based performance data as output from a check plugin
    into floating point numbers, do scaling if necessary.

    Simple example for perf_data: [(u'temp', u'48.1', u'', u'70', u'80', u'', u'')]
    Result for this example:
    { "temp" : {"value" : 48.1, "scalar": {"warn" : 70, "crit" : 80}, "unit" : { ... } }}
    """
    translated_metrics = {}
    color_index = 0
    for entry in perf_data:

        metric_name, new_entry = normalize_perf_data(entry, check_command)
        if metric_name in translated_metrics:
            continue  # ignore duplicate value

        mi, color_index = get_metric_info(metric_name, color_index)
        new_entry.update(mi)

        new_entry["unit"] = unit_info[new_entry["unit"]]

        translated_metrics[metric_name] = new_entry
    return translated_metrics


#.
#   .--Evaluation----------------------------------------------------------.
#   |          _____            _             _   _                        |
#   |         | ____|_   ____ _| |_   _  __ _| |_(_) ___  _ __             |
#   |         |  _| \ \ / / _` | | | | |/ _` | __| |/ _ \| '_ \            |
#   |         | |___ \ V / (_| | | |_| | (_| | |_| | (_) | | | |           |
#   |         |_____| \_/ \__,_|_|\__,_|\__,_|\__|_|\___/|_| |_|           |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |  Parsing of performance data into metrics, evaluation of expressions |
#   '----------------------------------------------------------------------'
# TODO: Refactor evaluate and all helpers into single class


def split_expression(expression):
    if "#" in expression:
        expression, explicit_color = expression.rsplit("#", 1)  # drop appended color information
    else:
        explicit_color = None

    if "@" in expression:
        expression, explicit_unit_name = expression.rsplit("@", 1)  # appended unit name
    else:
        explicit_unit_name = None
    return expression, explicit_unit_name, explicit_color


# Evaluates an expression, returns a triple of value, unit and color.
# e.g. "fs_used:max"    -> 12.455, "b", "#00ffc6",
# e.g. "fs_used(%)"     -> 17.5,   "%", "#00ffc6",
# e.g. "fs_used:max(%)" -> 100.0,  "%", "#00ffc6",
# e.g. 123.4            -> 123.4,  "",  None
# e.g. "123.4#ff0000"   -> 123.4,  "",  "#ff0000",
# Note:
# "fs_growth.max" is the same as fs_growth. The .max is just
# relevant when fetching RRD data and is used for selecting
# the consolidation function MAX.
def evaluate(expression, translated_metrics):
    if isinstance(expression, (float, int)):
        return _evaluate_literal(expression, translated_metrics)

    expression, explicit_unit_name, explicit_color = split_expression(expression)

    value, unit, color = _evaluate_rpn(expression, translated_metrics)

    if explicit_color:
        color = "#" + explicit_color

    if explicit_unit_name:
        unit = unit_info[explicit_unit_name]

    return value, unit, color


def _evaluate_rpn(expression, translated_metrics):
    parts = expression.split(",")
    stack = []  # stack tuples of (value, unit, color)
    while parts:
        operator_name = parts[0]
        parts = parts[1:]
        if operator_name in rpn_operators:
            if len(stack) < 2:
                raise MKGeneralException("Syntax error in expression '%s': too few operands" %
                                         expression)
            op1 = stack[-2]
            op2 = stack[-1]
            result = rpn_operators[operator_name](op1, op2)
            stack = stack[:-2] + [result]
        else:
            stack.append(_evaluate_literal(operator_name, translated_metrics))

    if len(stack) != 1:
        raise MKGeneralException("Syntax error in expression '%s': too many operands left" %
                                 expression)

    return stack[0]


# TODO: Do real unit computation, detect non-matching units
rpn_operators = {
    "+": lambda a, b: ((a[0] + b[0]), _unit_mult(a[1], b[1]), _choose_operator_color(a[2], b[2])),
    "-": lambda a, b: ((a[0] - b[0]), _unit_sub(a[1], b[1]), _choose_operator_color(a[2], b[2])),
    "*": lambda a, b: ((a[0] * b[0]), _unit_add(a[1], b[1]), _choose_operator_color(a[2], b[2])),
    "/": lambda a, b: ((a[0] / b[0]), _unit_div(a[1], b[1]), _choose_operator_color(a[2], b[2])),
    ">": lambda a, b: ((a[0] > b[0] and 1.0 or 0.0), unit_info[""], "#000000"),
    "<": lambda a, b: ((a[0] < b[0] and 1.0 or 0.0), unit_info[""], "#000000"),
    ">=": lambda a, b: ((a[0] >= b[0] and 1.0 or 0.0), unit_info[""], "#000000"),
    "<=": lambda a, b: ((a[0] <= b[0] and 1.0 or 0.0), unit_info[""], "#000000"),
    "MIN": lambda a, b: _operator_minmax(a, b, min),
    "MAX": lambda a, b: _operator_minmax(a, b, max),
}


# TODO: real unit computation!
def _unit_mult(u1, u2):
    if u1 == unit_info[""] or u1 == unit_info["count"]:
        return u2
    return u1


_unit_div = _unit_mult
_unit_add = _unit_mult
_unit_sub = _unit_mult


def _choose_operator_color(a, b):
    if a is None:
        return b
    elif b is None:
        return a
    return render_color(_mix_colors(parse_color(a), parse_color(b)))


def _operator_minmax(a, b, func):
    v = func(a[0], b[0])
    # Use unit and color of the winner. If the winner
    # has none (e.g. it is a scalar like 0), then take
    # unit and color of the loser.
    if v == a[0]:
        winner = a
        loser = b
    else:
        winner = b
        loser = a

    if winner[1] != unit_info[""]:
        unit = winner[1]
    else:
        unit = loser[1]

    return v, unit, winner[2] or loser[2]


def _evaluate_literal(expression, translated_metrics):
    if isinstance(expression, int):
        return float(expression), unit_info["count"], None

    elif isinstance(expression, float):
        return expression, unit_info[""], None

    elif expression[0].isdigit() or expression[0] == '-':
        return float(expression), unit_info[""], None

    if expression.endswith(".max") or expression.endswith(".min") or expression.endswith(
            ".average"):
        expression = expression.rsplit(".", 1)[0]

    color = None

    # TODO: Error handling with useful exceptions
    if expression.endswith("(%)"):
        percent = True
        expression = expression[:-3]
    else:
        percent = False

    if ":" in expression:
        varname, scalarname = expression.split(":")
        value = translated_metrics[varname]["scalar"].get(scalarname)
        color = scalar_colors.get(scalarname)
    else:
        varname = expression
        value = translated_metrics[varname]["value"]

    if percent:
        maxvalue = translated_metrics[varname]["scalar"]["max"]
        if maxvalue != 0:
            value = 100.0 * float(value) / maxvalue
        else:
            value = 0.0
        unit = unit_info["%"]

    else:
        unit = translated_metrics[varname]["unit"]

    if color is None:
        if varname in metric_info:
            color = parse_color_into_hexrgb(metric_info[varname]["color"])
        else:
            color = "#808080"
    return value, unit, color


#.
#   .--Graphs--------------------------------------------------------------.
#   |                    ____                 _                            |
#   |                   / ___|_ __ __ _ _ __ | |__  ___                    |
#   |                  | |  _| '__/ _` | '_ \| '_ \/ __|                   |
#   |                  | |_| | | | (_| | |_) | | | \__ \                   |
#   |                   \____|_|  \__,_| .__/|_| |_|___/                   |
#   |                                  |_|                                 |
#   +----------------------------------------------------------------------+
#   |  Implementation of time graphs - basic code, not the rendering       |
#   |  Rendering of the graphs is done by PNP4Nagios, we just create PHP   |
#   |  templates for PNP here.                                             |
#   '----------------------------------------------------------------------'


def get_graph_range(graph_template, translated_metrics):
    if "range" not in graph_template:
        return None, None  # Compute range of displayed data points

    try:
        return evaluate(graph_template["range"][0], translated_metrics)[0], \
               evaluate(graph_template["range"][1], translated_metrics)[0]
    except Exception:
        return None, None


def replace_expressions(text, translated_metrics):
    """Replace expressions in strings like CPU Load - %(load1:max@count) CPU Cores"""
    def eval_to_string(match):
        expression = match.group()[2:-1]
        value, unit, _color = evaluate(expression, translated_metrics)
        if value is not None:
            return unit["render"](value)
        return _("n/a")

    r = cmk.utils.regex.regex(r"%\([^)]*\)")
    return r.sub(eval_to_string, text)


def get_graph_template_choices():
    # TODO: v.get("title", k): Use same algorithm as used in
    # GraphIdentificationTemplateBased._parse_template_metric()
    return sorted([(k, v.get("title", k)) for k, v in graph_info.items()], key=lambda k_v: k_v[1])


def get_graph_template(template_id):
    if template_id.startswith("METRIC_"):
        return generic_graph_template(template_id[7:])
    elif template_id in graph_info:
        return graph_info[template_id]
    else:
        raise MKGeneralException(_("There is no graph template with the id '%d'") % template_id)


def generic_graph_template(metric_name):
    return {
        "id": "METRIC_" + metric_name,
        "metrics": [(metric_name, "area"),],
        "scalars": [
            metric_name + ":warn",
            metric_name + ":crit",
        ]
    }


def get_graph_templates(translated_metrics):
    if not translated_metrics:
        return []

    explicit_templates = _get_explicit_graph_templates(translated_metrics)
    already_graphed_metrics = _get_graphed_metrics(explicit_templates)
    implicit_templates = _get_implicit_graph_templates(translated_metrics, already_graphed_metrics)
    return explicit_templates + implicit_templates


def _get_explicit_graph_templates(translated_metrics):
    templates = []
    for graph_template in graph_info.values():
        if _graph_possible(graph_template, translated_metrics):
            templates.append(graph_template)
        elif _graph_possible_without_optional_metrics(graph_template, translated_metrics):
            templates.append(
                _graph_without_missing_optional_metrics(graph_template, translated_metrics))
    return templates


def _get_graphed_metrics(graph_templates):
    graphed_metrics = set([])
    for graph_template in graph_templates:
        graphed_metrics.update(_metrics_used_by_graph(graph_template))
    return graphed_metrics


def _get_implicit_graph_templates(translated_metrics, already_graphed_metrics):
    templates = []
    for metric_name, metric_entry in sorted(translated_metrics.items()):
        if metric_entry["auto_graph"] and metric_name not in already_graphed_metrics:
            templates.append(generic_graph_template(metric_name))
    return templates


def _metrics_used_by_graph(graph_template):
    used_metrics = []
    for metric_definition in graph_template["metrics"]:
        used_metrics += list(_metrics_used_in_definition(metric_definition[0]))
    return used_metrics


def _metrics_used_in_definition(metric_definition):
    without_color = metric_definition.split("#")[0]
    parts = without_color.split(",")
    for part in parts:
        metric_name = part.split(".")[0]  # drop .min, .max, .average
        if metric_name in rpn_operators:
            continue

        yield metric_name


def _graph_possible(graph_template, translated_metrics):
    for metric_definition in graph_template["metrics"]:
        try:
            evaluate(metric_definition[0], translated_metrics)
        except Exception:
            return False

    # Allow graphs to be disabled if certain (better) metrics
    # are available
    if "conflicting_metrics" in graph_template:
        for var in graph_template["conflicting_metrics"]:
            if var in translated_metrics:
                return False

    return True


def _graph_possible_without_optional_metrics(graph_template, translated_metrics):
    if "optional_metrics" in graph_template:
        return _graph_possible(
            graph_template, _add_fake_metrics(translated_metrics,
                                              graph_template["optional_metrics"]))


def _graph_without_missing_optional_metrics(graph_template, translated_metrics):
    working_metrics = []

    for metric_definition in graph_template["metrics"]:
        try:
            evaluate(metric_definition[0], translated_metrics)
            working_metrics.append(metric_definition)
        except Exception:
            pass

    reduced_graph_template = graph_template.copy()
    reduced_graph_template["metrics"] = working_metrics
    return reduced_graph_template


def _add_fake_metrics(translated_metrics, metric_names):
    with_fake = translated_metrics.copy()
    for metric_name in metric_names:
        with_fake[metric_name] = {
            "value": 1.0,
            "scale": 1.0,
            "unit": unit_info[""],
            "color": "#888888",
        }
    return with_fake


#.
#   .--Colors--------------------------------------------------------------.
#   |                      ____      _                                     |
#   |                     / ___|___ | | ___  _ __ ___                      |
#   |                    | |   / _ \| |/ _ \| '__/ __|                     |
#   |                    | |__| (_) | | (_) | |  \__ \                     |
#   |                     \____\___/|_|\___/|_|  |___/                     |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |  Functions and constants dealing with colors                         |
#   '----------------------------------------------------------------------'
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


def get_palette_color_by_index(i, shading='a'):
    color_key = sorted(_cmk_color_palette.keys())[i % len(_cmk_color_palette)]
    return "%s/%s" % (color_key, shading)


def get_next_random_palette_color():
    keys = _cmk_color_palette.keys()
    if 'random_color_index' in g:
        last_index = g.random_color_index
    else:
        last_index = random.randint(0, len(keys))
    index = (last_index + 1) % len(keys)
    g.random_color_index = index
    return parse_color_into_hexrgb("%s/a" % keys[index])


def get_n_different_colors(n):
    """Return a list of colors that are as different as possible (visually)
    by distributing them on the HSV color wheel."""
    total_weight = sum([x[1] for x in _hsv_color_distribution])

    colors = []
    while len(colors) < n:
        weight_index = int(len(colors) * total_weight / n)
        hue = _get_hue_by_weight_index(weight_index)
        colors.append(hsv_to_hexrgb((hue, 1, 1)))
    return colors


def _get_hue_by_weight_index(weight_index):
    section_begin = 0.0
    for section_end, section_weight in _hsv_color_distribution:
        if weight_index < section_weight:
            section_size = section_end - section_begin
            hue = section_begin + int((weight_index / section_weight) * section_size)
            return hue
        weight_index -= section_weight
        section_begin = section_end


# 23/c -> #ff8040
# #ff8040 -> #ff8040
def parse_color_into_hexrgb(color_string):
    if color_string[0] == "#":
        return color_string

    if "/" in color_string:
        cmk_color_index, color_shading = color_string.split("/")
        hsv = list(_cmk_color_palette[cmk_color_index])

        # Colors of the yellow ("2") and green ("3") area need to be darkened (in third place of the hsv tuple),
        # colors of the red and blue area need to be brightened (in second place of the hsv tuple).
        # For both shadings we need different factors.
        cmk_color_nuance_index = 1
        cmk_color_nuance_factor = 0.6

        if cmk_color_index[0] in ["2", "3"]:
            cmk_color_nuance_index = 2
            cmk_color_nuance_factor = 0.8

        if color_shading == 'b':
            hsv[cmk_color_nuance_index] *= cmk_color_nuance_factor

        color_hexrgb = hsv_to_hexrgb(hsv)
        return color_hexrgb

    return "#808080"


def hsv_to_hexrgb(hsv):
    return render_color(colorsys.hsv_to_rgb(*hsv))


def render_color(color_rgb):
    return "#%02x%02x%02x" % (
        int(color_rgb[0] * 255),
        int(color_rgb[1] * 255),
        int(color_rgb[2] * 255),
    )


# "#ff0080" -> (1.0, 0.0, 0.5)
def parse_color(color):
    try:
        return tuple([int(color[a:a + 2], 16) / 255.0 for a in (1, 3, 5)])
    except Exception:
        raise MKGeneralException(_("Invalid color specification '%s'") % color)


def fade_color(rgb, v):
    gray = _rgb_to_gray(rgb)
    if gray > 0.5:
        return darken_color(rgb, v)
    return lighten_color(rgb, v)


def darken_color(rgb, v):
    """Make a color darker. v ranges from 0 (not darker) to 1 (black)"""
    def darken(x, v):
        return x * (1.0 - v)

    return tuple([darken(x, v) for x in rgb])


def lighten_color(rgb, v):
    """Make a color lighter. v ranges from 0 (not lighter) to 1 (white)"""
    def lighten(x, v):
        return x + ((1.0 - x) * v)

    return tuple([lighten(x, v) for x in rgb])


def _rgb_to_gray(rgb):
    r, gr, b = rgb
    return 0.21 * r + 0.72 * gr + 0.07 * b


def _mix_colors(a, b):
    return tuple([(ca + cb) / 2.0 for (ca, cb) in zip(a, b)])


def render_color_icon(color):
    return html.render_div('', class_="color", style="background-color: %s" % color)


@MemoizeCache
def reverse_translate_metric_name(canonical_name):
    "Return all known perf data names that are translated into canonical_name"
    return set([
        metric for trans in check_metrics.values()
        for metric, options in trans.items() if options.get('name', '') == canonical_name
    ] + [canonical_name])
