#!/usr/bin/python
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
# ails.  You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

# Frequently used variable names:
# perf_data_string:   Raw performance data as sent by the core, e.g "foor=17M;1;2;4;5"
# perf_data:          Split performance data, e.g. [("foo", "17", "M", "1", "2", "4", "5")]
# translated_metrics: Completely parsed and translated into metrics, e.g. { "foo" : { "value" : 17.0, "unit" : { "render" : ... }, ... } }
# color:              RGB color representation ala HTML, e.g. "#ffbbc3" or "#FFBBC3", len() is always 7!
# color_rgb:          RGB color split into triple (r, g, b), where r,b,g in (0.0 .. 1.0)
# unit_name:          The ID of a unit, e.g. "%"
# unit:               The definition-dict of a unit like in unit_info
# graph_template:     Template for a graph. Essentially a dict with the key "metrics"

import math, time
import config, defaults, pagetypes, table
from lib import *
from valuespec import *
import livestatus


#   .--Plugins-------------------------------------------------------------.
#   |                   ____  _             _                              |
#   |                  |  _ \| |_   _  __ _(_)_ __  ___                    |
#   |                  | |_) | | | | |/ _` | | '_ \/ __|                   |
#   |                  |  __/| | |_| | (_| | | | | \__ \                   |
#   |                  |_|   |_|\__,_|\__, |_|_| |_|___/                   |
#   |                                 |___/                                |
#   +----------------------------------------------------------------------+
#   |  Typical code for loading Multisite plugins of this module           |
#   '----------------------------------------------------------------------'
# Datastructures and functions needed before plugins can be loaded
loaded_with_language = False

def load_plugins():
    global loaded_with_language

    if loaded_with_language == current_language:
        return

    global unit_info       ; unit_info       = {}
    global metric_info     ; metric_info     = {}
    global check_metrics   ; check_metrics   = {}
    global perfometer_info ; perfometer_info = []
    global graph_info      ; graph_info      = []
    load_web_plugins("metrics", globals())
    loaded_with_language = current_language


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
  m  : "m",
  1  : "",
  KB : "k",
  MB : "M",
  GB : "G",
  TB : "T",
  PB : "P",
  K  : "k",
  M  : "M",
  G  : "G",
  T  : "T",
  P  : "P",
}

scalar_colors = {
    "warn" : "#ffff00",
    "crit" : "#ff0000",
}


#.
#   .--Helpers-------------------------------------------------------------.
#   |                  _   _      _                                        |
#   |                 | | | | ___| |_ __   ___ _ __ ___                    |
#   |                 | |_| |/ _ \ | '_ \ / _ \ '__/ __|                   |
#   |                 |  _  |  __/ | |_) |  __/ |  \__ \                   |
#   |                 |_| |_|\___|_| .__/ \___|_|  |___/                   |
#   |                              |_|                                     |
#   +----------------------------------------------------------------------+
#   |  Various helper functions                                            |
#   '----------------------------------------------------------------------'

# "45.0" -> 45.0, "45" -> 45
def float_or_int(v):
    try:
        return int(v)
    except:
        return float(v)

def metric_to_text(metric, value=None):
    if value == None:
        value = metric["value"]
    return metric["unit"]["render"](value)

# A few helper function to be used by the definitions


# "#ff0080" -> (1.0, 0.0, 0.5)
def parse_color(color):
    return tuple([ int(color[a:a+2], 16) / 255.0 for a in (1,3,5) ])


def render_color(color_rgb):
    return "#%02x%02x%02x" % (
       int(color_rgb[0] * 255),
       int(color_rgb[1] * 255),
       int(color_rgb[2] * 255),)

# Make a color darker. v ranges from 0 (not darker) to 1 (black)
def darken_color(rgb, v):
    def darken(x, v):
        return x * (1.0 - v)
    return tuple([ darken(x, v) for x in rgb ])

# Make a color lighter. v ranges from 0 (not lighter) to 1 (white)
def lighten_color(rgb, v):
    def lighten(x, v):
        return x + ((1.0 - x) * v)
    return tuple([ lighten(x, v) for x in rgb ])

def mix_colors(a, b):
    return tuple([
       (ca + cb) / 2.0
       for (ca, cb)
       in zip(a, b)
    ])


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

# Convert perf_data_string into perf_data, extract check_command
def parse_perf_data(perf_data_string, check_command=None):
    # Strip away arguments like in "check_http!-H mathias-kettner.de"
    check_command = check_command.split("!")[0]

    if not perf_data_string:
        return None, check_command

    parts = perf_data_string.split()

    # Try if check command is appended to performance data
    # in a PNP like style
    if parts[-1].startswith("[") and parts[-1].endswith("]"):
        check_command = parts[-1][1:-1]
        del parts[-1]

    # Python's isdigit() works only on str. We deal with unicode since
    # we deal with data coming from Livestatus
    def isdigit(x):
        return x in [ '0', '1', '2', '3', '4', '5', '6', '7', '8', '9' ]

    # Parse performance data, at least try
    try:
        perf_data = []
        for part in parts:
            varname, values = part.split("=")
            value_parts = values.split(";")
            while len(value_parts) < 5:
                value_parts.append(None)
            value, warn, crit, min, max = value_parts[0:5]
            # separate value from unit
            i = 0
            while i < len(value) and (isdigit(value[i]) or value[i] in ['.', ',', '-']):
                i += 1
            unit_name = value[i:]
            value = value[:i]
            perf_data.append((varname, value, unit_name, warn, crit, min, max))
    except:
        if config.debug:
            raise
        perf_data = None

    return perf_data, check_command



# Convert Ascii-based performance data as output from a check plugin
# into floating point numbers, do scaling if neccessary.
# Simple example for perf_data: [(u'temp', u'48.1', u'', u'70', u'80', u'', u'')]
# Result for this example:
# { "temp" : "value" : 48.1, "warn" : 70, "crit" : 80, "unit" : { ... } }
def translate_metrics(perf_data, check_command):
    if check_command not in check_metrics:
        return None

    cm = check_metrics[check_command]

    translated_metrics = {}
    for nr, entry in enumerate(perf_data):
        varname = entry[0]

        translation_entry = {} # Default: no translation neccessary

        if varname in cm:
            translation_entry = cm[varname]
        else:
            for orig_varname, te in cm.items():
                if orig_varname[0] == "~" and regex(orig_varname[1:]).match(varname): # Regex entry
                    translation_entry = te
                    break


        # Translate name
        metric_name = translation_entry.get("name", varname)

        if metric_name not in metric_info:
            mi = {
                "title" : metric_name,
                "unit" : "count",
                "color" : "#888888",
            }
        else:
            mi = metric_info[metric_name]

        # Optional scaling
        scale = translation_entry.get("scale", 1.0)

        new_entry = {
            "value"      : float_or_int(entry[1]) * scale,
            "orig_name"  : varname,
            "scale"      : scale, # needed for graph definitions
            "scalar"     : {},
        }

        # Add warn, crit, min, max
        for index, key in [ (3, "warn"), (4, "crit"), (5, "min"), (6, "max") ]:
            if len(entry) < index + 1:
                break
            elif entry[index]:
                try:
                    value = float_or_int(entry[index])
                    new_entry["scalar"][key] = value * scale
                except:
                    if config.debug:
                        raise
                    pass # empty of invalid number


        new_entry.update(mi)
        new_entry["unit"] = unit_info[new_entry["unit"]]
        translated_metrics[metric_name] = new_entry
        # TODO: warn, crit, min, max
        # if entry[2]:
        #     # TODO: lower and upper levels
        #     translated_metrics[metric_name]["warn"] = float(entry[2])
    return translated_metrics


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
    if type(expression) in (float, int) or "," not in expression:
        return evaluate_literal(expression, translated_metrics)
    else:
        if "#" in expression:
            expression, explicit_color = expression.rsplit("#", 1) # drop appended color information
        else:
            explicit_color = None

        if "@" in expression:
            expression, explicit_unit_name = expression.rsplit("@", 1) # appended unit name
        else:
            explicit_unit_name = None

        value, unit, color = evaluate_rpn(expression, translated_metrics)

        if explicit_color:
            color = "#" + explicit_color

        if explicit_unit_name:
            unit = unit_info[explicit_unit_name]

        return value, unit, color


# TODO: real unit computation!
def unit_mult(u1, u2):
    if u1 == unit_info[""] or u1 == unit_info["count"]:
        return u2
    else:
        return u1

def unit_add(u1, u2):
    return unit_mult(u1, u2)

def unit_sub(u1, u2):
    return unit_mult(u1, u2)

def operator_minmax(a, b, func):
    v = func(a[0], b[0])
    # Use unit and color of the winner. If the winner
    # has none (e.g. it is a scalar like 0), then take
    # unit and color of the looser.
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


# TODO: Do real unit computation, detect non-matching units
rpn_operators = {
    "+"  : lambda a, b: ((a[0] +  b[0]),                unit_mult(a[1], b[1]), choose_operator_color(a[2], b[2])),
    "-"  : lambda a, b: ((a[0] -  b[0]),                unit_mult(a[1], b[1]), choose_operator_color(a[2], b[2])),
    "*"  : lambda a, b: ((a[0] *  b[0]),                unit_mult(a[1], b[1]), choose_operator_color(a[2], b[2])),
    "/"  : lambda a, b: ((a[0] /  b[0]),                unit_info[""],         choose_operator_color(a[2], b[2])),
    ">"  : lambda a, b: ((a[0] >  b[0] and 1.0 or 0.0), unit_info[""],         "#000000"),
    "<"  : lambda a, b: ((a[0] <  b[0] and 1.0 or 0.0), unit_info[""],         "#000000"),
    ">=" : lambda a, b: ((a[0] >= b[0] and 1.0 or 0.0), unit_info[""],         "#000000"),
    "<=" : lambda a, b: ((a[0] <= b[0] and 1.0 or 0.0), unit_info[""],         "#000000"),
    "MIN" : lambda a, b: operator_minmax(a, b, min),
    "MAX" : lambda a, b: operator_minmax(a, b, max),
}

def choose_operator_color(a, b):
    if a == None:
        return b
    elif b == None:
        return a
    else:
        return render_color(mix_colors(parse_color(a), parse_color(b)))


def evaluate_rpn(expression, translated_metrics):
    parts = expression.split(",")
    stack = [] # stack tuples of (value, unit, color)
    while parts:
        operator_name = parts[0]
        parts = parts[1:]
        if operator_name in rpn_operators:
            if len(stack) < 2:
                raise MKGeneralException("Syntax error in expression '%s': too few operands" % expression)
            op1 = stack[-2]
            op2 = stack[-1]
            result = rpn_operators[operator_name](op1, op2)
            stack = stack[:-2] + [ result ]
        else:
            stack.append(evaluate_literal(operator_name, translated_metrics))

    if len(stack) != 1:
        raise MKGeneralException("Syntax error in expression '%s': too many operands left" % expression)

    return stack[0]


def evaluate_literal(expression, translated_metrics):

    if type(expression) == int:
        return float(expression), unit_info["count"], None

    elif type(expression) == float:
        return expression, unit_info[""], None

    elif expression[0].isdigit() or expression[0] == '-':
        return float(expression), unit_info[""], None

    if expression.endswith(".max") or expression.endswith(".min") or expression.endswith(".average"):
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

    if color == None:
        color = metric_info[varname]["color"]
    return value, unit, color


# Replace expressions in strings like CPU Load - %(load1:max@count) CPU Cores"
def replace_expressions(text, translated_metrics):
    def eval_to_string(match):
        expression = match.group()[2:-1]
        unit_name = None
        if "@" in expression:
            expression, unit_name = expression.split("@")
        value, unit, color = evaluate(expression, translated_metrics)
        if unit_name:
            unit = unit_info[unit_name]
        if value != None:
            return unit["render"](value)
        else:
            return _("n/a")

    r = regex(r"%\([^)]*\)")
    return r.sub(eval_to_string, text)

#.
#   .--Perf-O-Meters-------------------------------------------------------.
#   |  ____            __        ___        __  __      _                  |
#   | |  _ \ ___ _ __ / _|      / _ \      |  \/  | ___| |_ ___ _ __ ___   |
#   | | |_) / _ \ '__| |_ _____| | | |_____| |\/| |/ _ \ __/ _ \ '__/ __|  |
#   | |  __/  __/ |  |  _|_____| |_| |_____| |  | |  __/ ||  __/ |  \__ \  |
#   | |_|   \___|_|  |_|        \___/      |_|  |_|\___|\__\___|_|  |___/  |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |  Implementation of Perf-O-Meters                                     |
#   '----------------------------------------------------------------------'

def get_perfometers(translated_metrics):
    for perfometer in perfometer_info:
        if perfometer_possible(perfometer, translated_metrics):
            yield perfometer


# TODO: We will run into a performance problem here when we
# have more and more Perf-O-Meter definitions.
# TODO: remove all tuple-perfometers and use dicts
def perfometer_possible(perfometer, translated_metrics):

    if type(perfometer) == dict:
        if perfometer["type"] == "linear":
            required = perfometer["segments"][:]
        elif perfometer["type"] == "logarithmic":
            required = [ perfometer["metric"] ]
        else:
            pass # TODO: dual, stacked?

        if "label" in perfometer and perfometer["label"] != None:
            required.append(perfometer["label"][0])
        if "total" in perfometer:
            required.append(perfometer["total"])

        for req in required:
            try:
                evaluate(req, translated_metrics)
            except:
                return False

        if "condition" in perfometer:
            try:
                value, color, unit = evaluate(perfometer["condition"], translated_metrics)
                if value == 0.0:
                    return False
            except:
                return False

        return True



    perf_type, perf_args = perfometer

    if perf_type == "logarithmic":
        required = [ perf_args[0] ]

    elif perf_type == "linear":
        required = perf_args[0]
        if perf_args[1]:
            required = required + [perf_args[1]] # Reference value for 100%
        if perf_args[2]:
            required = required + [perf_args[2]] # Labelling value

    elif perf_type in ("stacked", "dual"):
        for sub_perf in perf_args:
            if not perfometer_possible(sub_perf, translated_metrics):
                return False
        return True

    else:
        raise MKInternalError(_("Undefined Perf-O-Meter type '%s'") % perf_type)

    for req in required:
        try:
            evaluate(req, translated_metrics)
        except:
            return False
    return True


def metricometer_logarithmic(value, half_value, base, color):
    # Negative values are printed like positive ones (e.g. time offset)
    value = abs(float(value))
    if value == 0.0:
        pos = 0
    else:
        half_value = float(half_value)
        h = math.log(half_value, base) # value to be displayed at 50%
        pos = 50 + 10.0 * (math.log(value, base) - h)
        if pos < 2:
            pos = 2
        if pos > 98:
            pos = 98

    return [ (pos, color), (100 - pos, "#ffffff") ]


def build_perfometer(perfometer, translated_metrics):
    # TODO: alle nicht-dict Perfometer umstellen
    if type(perfometer) == dict:
        if perfometer["type"] == "logarithmic":
            value, unit, color = evaluate(perfometer["metric"], translated_metrics)
            label = unit["render"](value)
            stack = [ metricometer_logarithmic(value, perfometer["half_value"], perfometer["exponent"], color) ]

        elif perfometer["type"] == "linear":
            entry = []
            stack = [entry]

            summed = 0.0

            for ex in perfometer["segments"]:
                value, unit, color = evaluate(ex, translated_metrics)
                summed += value

            if "total" in perfometer:
                total, unit, color = evaluate(perfometer["total"], translated_metrics)
            else:
                total = summed

            if total == 0:
                entry.append((100.0, "#ffffff"))

            else:
                for ex in perfometer["segments"]:
                    value, unit, color = evaluate(ex, translated_metrics)
                    entry.append((100.0 * value / total, color))

                # Paint rest only, if it is positive and larger than one promille
                if total - summed > 0.001:
                    entry.append((100.0 * (total - summed) / total, "#ffffff"))

            # Use unit of first metrics for output of sum. We assume that all
            # stackes metrics have the same unit anyway
            value, unit, color = evaluate(perfometer["segments"][0], translated_metrics)
            label = unit["render"](summed)

        # "label" option in all Perf-O-Meters overrides automatic label
        if "label" in perfometer:
            if perfometer["label"] == None:
                label = ""
            else:
                expr, unit_name = perfometer["label"]
                value, unit, color = evaluate(expr, translated_metrics)
                if unit_name:
                    unit = unit_info[unit_name]
                label = unit["render"](value)

        return label, stack



    # This stuf is deprecated and will be removed soon. Watch out!
    perfometer_type, definition = perfometer

    if perfometer_type == "logarithmic":
        expression, median, exponent = definition
        value, unit, color = evaluate(expression, translated_metrics)
        label = unit["render"](value)
        stack = [ metricometer_logarithmic(value, median, exponent, color) ]

    # TODO: das hier fliegt raus
    elif perfometer_type == "linear":
        entry = []
        stack = [entry]

        # NOTE: This might be converted to a dict later.
        metrics_expressions, total_spec, label_expression = definition
        summed = 0.0

        for ex in metrics_expressions:
            value, unit_name, color = evaluate(ex, translated_metrics)
            summed += value

        if total_spec == None:
            total = summed
        else:
            total, unit_name, color = evaluate(total_spec, translated_metrics)

        if total == 0:
            entry.append((100.0, "#ffffff"))

        else:
            for ex in metrics_expressions:
                value, unit_name, color = evaluate(ex, translated_metrics)
                entry.append((100.0 * value / total, color))

            # Paint rest only, if it is positive and larger than one promille
            if total - summed > 0.001:
                entry.append((100.0 * (total - summed) / total, "#ffffff"))

        # Use unit of first metrics for output of sum. We assume that all
        # stackes metrics have the same unit anyway
        if label_expression:
            expr, unit_name = label_expression
            value, unit, color = evaluate(expr, translated_metrics)
            if unit_name:
                unit = unit_info[unit_name]
            label = unit["render"](summed)
        else: # absolute
            value, unit, color = evaluate(metrics_expressions[0], translated_metrics)
            label = unit["render"](summed)

    elif perfometer_type == "stacked":
        stack = []
        labels = []
        for sub_perf in definition:
            sub_label, sub_stack = build_perfometer(sub_perf, translated_metrics)
            stack.append(sub_stack[0])
            if sub_label:
                labels.append(sub_label)
        if labels:
            label = " / ".join(labels)
        else:
            label = ""
        return label, stack

    elif perfometer_type == "dual":
        labels = []
        if len(definition) != 2:
            raise MKInternalError(_("Perf-O-Meter of type 'dual' must contain exactly two definitions, not %d") % len(definition))

        content = []
        for nr, sub_perf in enumerate(definition):
            sub_label, sub_stack = build_perfometer(sub_perf, translated_metrics)
            if len(sub_stack) != 1:
                raise MKInternalError(_("Perf-O-Meter of type 'dual' must only contain plain Perf-O-Meters"))

            half_stack = [ (value/2, color) for (value, color) in sub_stack[0] ]
            if nr == 0:
                half_stack.reverse()
            content += half_stack
            if sub_label:
                labels.append(sub_label)

        if labels:
            label = " / ".join(labels)
        else:
            label = ""
        return label, [ content ]


    else:
        raise MKInternalError(_("Unsupported Perf-O-Meter type '%s'") % perfometer_type)

    return label, stack




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
#   |  templates for PNP here.
#   '----------------------------------------------------------------------'

def get_graph_templates(translated_metrics):
    for graph_template in graph_info:
        if graph_possible(graph_template, translated_metrics):
            yield graph_template


def graph_possible(graph_template, translated_metrics):
    for metric_definition in graph_template["metrics"]:
        try:
            evaluate(metric_definition[0], translated_metrics)
        except Exception, e:
            return False

    # Allow graphs to be disabled if certain (better) metrics
    # are available
    if "not_if_have" in graph_template:
        for var in graph_template["not_if_have"]:
            if var in translated_metrics:
                return False

    return True

# Called with exactly one variable: the template ID. Example:
# "check_mk-kernel.util:guest,steal,system,user,wait".
def page_pnp_template():

    template_id = html.var("id")
    check_command, perf_var_string = template_id.split(":", 1)
    perf_var_names = perf_var_string.split(",")

    # Fake performance values in order to be able to find possible graphs
    perf_data = [ ( varname, 1, "", 1, 1, 1, 1 ) for varname in perf_var_names ]
    translated_metrics = translate_metrics(perf_data, check_command)
    if not translated_metrics:
        return # check not supported

    # Collect output in string. In case of an exception to not output
    # any definitions
    output = ""
    for graph_template in get_graph_templates(translated_metrics):
        graph_code = render_graph_pnp(graph_template, translated_metrics)
        output += graph_code

    html.write(output)


def render_graph_pnp(graph_template, translated_metrics):

    graph_title = None
    vertical_label = None

    rrdgraph_commands = ""

    legend_precision    = graph_template.get("legend_precision", 2)
    legend_scale        = graph_template.get("legend_scale", 1)
    legend_scale_symbol = scale_symbols[legend_scale]

    # Define one RRD variable for each of the available metrics.
    # Note: We need to use the original name, not the translated one.
    for var_name, metrics in translated_metrics.items():
        rrd = "$RRDBASE$_" + pnp_cleanup(metrics["orig_name"]) + ".rrd"
        scale = metrics["scale"]
        unit = metrics["unit"]
        render_scale = unit.get("render_scale", 1)

        if scale != 1.0 or render_scale != 1.0:
            rrdgraph_commands += "DEF:%s_UNSCALED=%s:1:MAX " % (var_name, rrd)
            rrdgraph_commands += "CDEF:%s=%s_UNSCALED,%f,* " % (var_name, var_name, scale * render_scale)

        else:
            rrdgraph_commands += "DEF:%s=%s:1:MAX " % (var_name, rrd)

        # Scaling for legend
        rrdgraph_commands += "CDEF:%s_LEGSCALED=%s,%f,/ " % (var_name, var_name, legend_scale)

        # Prepare negative variants for upside-down graph
        rrdgraph_commands += "CDEF:%s_NEG=%s,-1,* " % (var_name, var_name)
        rrdgraph_commands += "CDEF:%s_LEGSCALED_NEG=%s_LEGSCALED,-1,* " % (var_name, var_name)


    # Compute width of columns in case of mirrored legend

    mirror_legend = graph_template.get("mirror_legend")
    total_width = 89 # characters
    left_width = max([len(_("Average")), len(_("Maximum")), len(_("Last"))]) + 2
    column_width = (total_width - left_width) / len(graph_template["metrics"]) - 2

    # Now add areas and lines to the graph
    graph_metrics = []

    # Graph with upside down metrics? (e.g. for Disk IO)
    have_upside_down = False

    # Compute width of the right column of the legend
    if not mirror_legend:
        max_title_length = 0
        for nr, metric_definition in enumerate(graph_template["metrics"]):
            if len(metric_definition) >= 3:
                title = metric_definition[2]
            elif not "," in metric_definition:
                title = metric_info[metric_definition[0].split("#")[0]]["title"]
            else:
                title = ""
            max_title_length = max(max_title_length, len(title))


    for nr, metric_definition in enumerate(graph_template["metrics"]):
        metric_name = metric_definition[0]
        line_type = metric_definition[1] # "line", "area", "stack"

        # Optional title, especially for derived values
        if len(metric_definition) >= 3:
            title = metric_definition[2]
        else:
            title = ""

        # Prefixed minus renders the metrics in negative direction
        if line_type[0] == '-':
            have_upside_down = True
            upside_down = True
            upside_down_factor = -1
            line_type = line_type[1:]
            upside_down_suffix = "_NEG"
        else:
            upside_down = False
            upside_down_factor = 1
            upside_down_suffix = ""

        if line_type == "line":
            draw_type = "LINE"
            draw_stack = ""
        elif line_type == "area":
            draw_type = "AREA"
            draw_stack = ""
        elif line_type == "stack":
            draw_type = "AREA"
            draw_stack = ":STACK"

        # User can specify alternative color using a suffixed #aabbcc
        if '#' in metric_name:
            metric_name, custom_color = metric_name.split("#", 1)
        else:
            custom_color = None

        commands = ""
        # Derived value with RBN syntax (evaluated by RRDTool!).
        if "," in metric_name:
            # We evaluate just in order to get color and unit.
            # TODO: beware of division by zero. All metrics are set to 1 here.
            value, unit, color = evaluate(metric_name, translated_metrics)

            # Choose a unique name for the derived variable and compute it
            commands += "CDEF:DERIVED%d=%s " % (nr , metric_name)
            if upside_down:
                commands += "CDEF:DERIVED%d_NEG=DERIVED%d,-1,* " % (nr, nr)

            metric_name = "DERIVED%d" % nr
            # Scaling and upsidedown handling for legend
            commands += "CDEF:%s_LEGSCALED%s=%s,%f,/ " % (metric_name, upside_down_suffix, metric_name, legend_scale * upside_down_factor)

        else:
            mi = metric_info[metric_name]
            if not title:
                title = mi["title"]
            color = mi["color"]
            unit = unit_info[mi["unit"]]

        if custom_color:
            color = "#" + custom_color

        # Paint the graph itself
        # TODO: Die Breite des Titels intelligent berechnen. Bei legend = "mirrored" muss man die
        # Vefügbare Breite ermitteln und aufteilen auf alle Titel
        if mirror_legend:
            left_pad = " " * int((column_width - len(title) - 4 + (nr*0.63)))
            commands += "COMMENT:\"%s\" " % left_pad
            right_pad = ""
        else:
            right_pad = " " * (max_title_length - len(title))
        commands += "%s:%s%s%s:\"%s%s\"%s " % (draw_type, metric_name, upside_down_suffix, color, title, right_pad, draw_stack)
        if line_type == "area":
            commands += "LINE:%s%s%s " % (metric_name, upside_down_suffix, render_color(darken_color(parse_color(color), 0.2)))

        unit_symbol = unit["symbol"]
        if unit_symbol == "%":
            unit_symbol = "%%"
        else:
            unit_symbol = " " + unit_symbol

        graph_metrics.append((metric_name, unit_symbol, commands))

        # Use title and label of this metrics as default for the graph
        if title and not graph_title:
            graph_title = title
        if not vertical_label:
            vertical_label = unit["title"]


    # Now create the rrdgraph commands for all metrics - according to the choosen layout
    if mirror_legend:
        for what, what_title in [ ("command", ""), ("AVERAGE", _("Average") + "\\:"), ("MAX", _("Maximum") + "\\:"), ("LAST", _("Last") + "\\:") ]:
            rrdgraph_commands += "COMMENT:\"%%-%ds\" " % left_width % what_title
            for metric_name, unit_symbol, commands in graph_metrics:
                if what == "command":
                    rrdgraph_commands += commands
                else:
                    legend_symbol = unit_symbol
                    if unit_symbol and unit_symbol[0] == " ":
                        legend_symbol = " %s%s" % (legend_scale_symbol, unit_symbol[1:])
                    rrdgraph_commands += "GPRINT:%%s_LEGSCALED:%%s:\"%%%%%d.%dlf%%s\" " % (column_width - len(legend_scale_symbol), legend_precision) \
                           % (metric_name, what, legend_symbol)
            rrdgraph_commands += "COMMENT:\"\\n\" "

    # Normal legend where for each metric there is one line containing average, max and last
    else:
        for metric_name, unit_symbol, commands in graph_metrics:
            rrdgraph_commands += commands
            legend_symbol = unit_symbol
            if unit_symbol and unit_symbol[0] == " ":
                legend_symbol = " %s%s" % (legend_scale_symbol, unit_symbol[1:])
            for what, what_title in [ ("AVERAGE", _("average")), ("MAX", _("max")), ("LAST", _("last")) ]:
                rrdgraph_commands += "GPRINT:%%s_LEGSCALED:%%s:\"%%%%8.%dlf%%s %%s\" "  % legend_precision % \
                            (metric_name, what, legend_symbol, what_title)
            rrdgraph_commands += "COMMENT:\"\\n\" "


    # For graphs with both up and down, paint a gray rule at 0
    if have_upside_down:
        rrdgraph_commands += "HRULE:0#c0c0c0 "

    # Now compute the arguments for the command line of rrdgraph
    rrdgraph_arguments = ""

    graph_title = graph_template.get("title", graph_title)
    vertical_label = graph_template.get("vertical_label", vertical_label)

    rrdgraph_arguments += "--vertical-label %s --title %s -L 4" % (
        quote_shell_string(vertical_label),
        quote_shell_string(graph_title))

    if "range" in graph_template:
        rrdgraph_arguments += " -l %f -u %f" % graph_template["range"]
    else:
        rrdgraph_arguments += " -l 0"


    # Some styling options, currently hardcoded
    rrdgraph_arguments += " --color MGRID\"#cccccc\" --color GRID\"#dddddd\" --width=600";

    return graph_title + "\n" + rrdgraph_arguments + "\n" + rrdgraph_commands + "\n"



#.
#   .--Hover-Graph---------------------------------------------------------.
#   |     _   _                           ____                 _           |
#   |    | | | | _____   _____ _ __      / ___|_ __ __ _ _ __ | |__        |
#   |    | |_| |/ _ \ \ / / _ \ '__|____| |  _| '__/ _` | '_ \| '_ \       |
#   |    |  _  | (_) \ V /  __/ | |_____| |_| | | | (_| | |_) | | | |      |
#   |    |_| |_|\___/ \_/ \___|_|        \____|_|  \__,_| .__/|_| |_|      |
#   |                                                   |_|                |
#   '----------------------------------------------------------------------'

def page_show_graph():
    site = html.var('site')
    host_name = html.var('host_name')
    service = html.var('service')

    # FIXME HACK TODO We don't have the current perfata and check command
    # here, but we only need it till metrics.render_svc_time_graph() does
    # not need these information anymore.
    if service == "_HOST_":
        query = "GET hosts\n" \
                "Filter: host_name = %s\n" \
                "Columns: perf_data metrics check_command\n" % host_name

    else:
        query = "GET services\n" \
                "Filter: host_name = %s\n" \
                "Filter: service_description = %s\n" \
                "Columns: perf_data metrics check_command\n" % (host_name, service)

    html.live.set_only_sites([site])
    try:
        data = html.live.query_row(query)
    except livestatus.MKLivestatusNotFoundError:
        html.write('<div class="error">%s</div>' %
            _('Failed to fetch data for graph. Maybe the site is not reachable?'))
        return
    html.live.set_only_sites(None)

    if service == "_HOST_":
        row = {
            'site'                  : site,
            'host_name'             : host_name,
            'host_perf_data'        : data[0],
            'host_metrics'          : data[1],
            'host_check_command'    : data[2],
        }
    else:
        row = {
            'site'                  : site,
            'host_name'             : host_name,
            'service_description'   : service,
            'service_perf_data'     : data[0],
            'service_metrics'       : data[1],
            'service_check_command' : data[2],
        }

    # now try to render the graph with our graphing. If it is not possible,
    # add JS code to let browser fetch the PNP graph
    try:
        # Currently always displaying 24h graph
        end_time = time.time()
        start_time = end_time - 8 * 3600

        htmlcode = render_time_graph(row, start_time, end_time, size=(30, 10), font_size=8, show_legend=False, graph_id_prefix="hover")
        if htmlcode:
            html.write(htmlcode)
            return
    except NameError:
        if config.debug:
            raise
        pass

    # Fallback to PNP graph rendering
    host = pnp_cleanup(host_name)
    svc = pnp_cleanup(service)
    site = html.site_status[site]["site"]
    if html.mobile:
        url = site["url_prefix"] + ("pnp4nagios/index.php?kohana_uri=/mobile/popup/%s/%s" % \
            (html.urlencode(host), html.urlencode(svc)))
    else:
        url = site["url_prefix"] + ("pnp4nagios/index.php/popup?host=%s&srv=%s" % \
            (html.urlencode(host), html.urlencode(svc)))

    html.write(url)
