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

# Frequently used variable names an terms
# perf_data_string:   Raw performance data as sent by the core, e.g "foor=17M;1;2;4;5"
# perf_data:          Split performance data, e.g. [("foo", "17", "M", "1", "2", "4", "5")]
# translated_metrics: Completely parsed and translated into metrics, e.g. { "foo" : { "value" : 17.0, "unit" : { "render" : ... }, ... } }
# color:              RGB color representation ala HTML, e.g. "#ffbbc3" or "#FFBBC3", len() is always 7!
# color_rgb:          RGB color split into triple (r, g, b), where r,b,g in (0.0 .. 1.0)

import math
import config, defaults
from lib import *

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


# Definitions to be used in the actual metric declarations

KB = 1024
MB = 1024 * 1024
GB = 1024 * 1024 * 1024
TB = 1024 * 1024 * 1024 * 1024
PB = 1024 * 1024 * 1024 * 1024 * 1024


# Convert perf_data_string into perf_data, extract check_command
def parse_perf_data(perf_data_string, check_command=None):
    parts = perf_data_string.split()
    # Try if check command is appended to performance data
    # in a PNP like style
    if parts[-1].startswith("[") and parts[-1].endswith("]"):
        check_command = parts[-1][1:-1]
        del parts[-1]

    # Strip away arguments like in "check_http!-H mathias-kettner.de"
    check_command = check_command.split("!")[0]

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
            unit = value[i:]
            value = value[:i]
            perf_data.append((varname, value, unit, warn, crit, min, max))
    except:
        if config.debug:
            raise
        perf_data = None

    return perf_data, check_command



# "45.0" -> 45.0, "45" -> 45
def float_or_int(v):
    try:
        return int(v)
    except:
        return float(v)


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
        if nr in cm:
            translation_entry = cm[nr]  # access by index of perfdata (e.g. in filesystem)
        else:
            translation_entry = cm.get(varname, {})

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
        scale = translation_entry.get("scale", 1)

        new_entry = {
            "value"     : float_or_int(entry[1]) * scale,
            "orig_name" : varname,
            "scalar"    : {},
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


# Evaluates an expression, returns the value and the unit.
# e.g. "fs_used:max"    -> 12.455, "b"
# e.g. "fs_used(%)"     -> 17.5,   "%"
# e.g. "fs_used:max(%)" -> 100.0,  "%"
def evaluate(expression, translated_metrics):
    if type(expression) in (float, int) or "," not in expression:
        return evaluate_literal(expression, translated_metrics)
    else:
        return evaluate_rpn(expression, translated_metrics)

# TODO: Do real unit computation, detect non-matching units
rpn_operators = {
    "+" : lambda a, b: ((a[0] + b[0]), a[1]),
    "-" : lambda a, b: ((a[0] - b[0]), a[1]),
    "*" : lambda a, b: ((a[0] * b[0]), a[1]+b[1]),
    "/" : lambda a, b: ((a[0] / b[0]), ""),
}


def evaluate_rpn(expression, translated_metrics):
    parts = expression.split(",")
    stack = [] # stack pairs of (value, unit)
    while parts:
        operator_name = parts[0]
        parts = parts[1:]
        if operator_name in rpn_operators:
            if len(stack) < 2:
                raise MKGeneralException("Syntax error in expression '%s': too few operands" % expression)
            op1 = stack[-1]
            op2 = stack[-2]
            stack = stack[:-2] + [ rpn_operators[operator_name](op1, op2) ]
        else:
            stack.append(evaluate_literal(operator_name, translated_metrics))

    if len(stack) != 1:
        raise MKGeneralException("Syntax error in expression '%s': too many operands left" % expression)

    return stack[0]


def evaluate_literal(expression, translated_metrics):
    if type(expression) == int:
        return expression, "count"
    elif type(expression) == float:
        return expression, None

    # TODO: Error handling with useful exceptions
    if expression.endswith("(%)"):
        percent = True
        expression = expression[:-3]
    else:
        percent = False

    if ":" in expression:
        varname, scalarname = expression.split(":")
        value = translated_metrics[varname]["scalar"].get(scalarname)
    else:
        varname = expression
        value = translated_metrics[varname]["value"]

    if percent:
        value = float(value) / translated_metrics[varname]["scalar"]["max"] * 100.0
        unit = "%"

    else:
        unit = translated_metrics[varname]["unit"]

    return value, unit


# e.g. "fs_used:max(%)" -> "fs_used"
def get_name(expression):
    if type(expression) in (int, float):
        return None
    if expression.endswith("(%)"):
        expression = expression[:-3]
    return expression.split(":")[0]

def get_color(expression):
    name = get_name(expression)
    if name:
        return metric_info[name]["color"]
    else:
        return "#808080"

def get_unit(expression):
    if expression.endswith("(%)"):
        return unit_info["%"]
    else:
        return unit_info[metric_info[get_name(expression)]["unit"]]


def get_perfometers(translated_metrics):
    for perfometer in perfometer_info:
        if perfometer_possible(perfometer, translated_metrics):
            yield perfometer


# TODO: We will run into a performance problem here when we
# have more and more Perf-O-Meter definitions.
def perfometer_possible(perfometer, translated_metrics):
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

def get_graphs(translated_metrics):
    for graph in graph_info:
        if graph_possible(graph, translated_metrics):
            yield graph

def graph_possible(graph, translated_metrics):
    for metric_definition in graph["metrics"]:
        try:
            evaluate(metric_definition[0], translated_metrics)
        except:
            return False
    return True


def metric_to_text(metric, value=None):
    if value == None:
        value = metric["value"]
    return metric["unit"]["render"](value)

def value_to_text(value, unit):
    return unit_info[unit]["render"](value)

# A few helper function to be used by the definitions
# 45.1 -> "45.1"
# 45.0 -> "45"
def drop_dotzero(v):
    t = "%.1f" % v
    if t.endswith(".0"):
        return t[:-2]
    else:
        return t


def frexp10(x):
    exp = int(math.log10(x))
    mantissa = x / 10**exp
    if mantissa < 1:
        mantissa *= 10
        exp -= 1
    return mantissa, exp

# Render a physical value witha precision of p
# digits. Use K (kilo), M (mega), m (milli), µ (micro)
# p is the number of non-zero digits - not the number of
# decimal places.
# Examples for p = 3:
# a: 0.0002234   b: 4,500,000  c: 137.56
# Result:
# a: 223 µ       b: 4.50 M     c: 138

# Note if the type of v is integer, then the precision cut
# down to the precision of the actual number
def physical_precision(v, precision, unit):
    if v == 0:
        return "%%.%df" % (precision - 1) % v
    elif v < 0:
        return "-" + physical_precision(-v, precision, unit)

    # Splitup in mantissa (digits) an exponent to the power of 10
    # -> a: (2.23399998, -2)  b: (4.5, 6)    c: (1.3756, 2)
    mantissa, exponent = frexp10(float(v))

    if type(v) == int:
        precision = min(precision, exponent + 1)

    # Round the mantissa to the required number of digits
    # -> a: 2.23              b: 4.5         c: 1.38
    mant_rounded = round(mantissa, precision-1) * 10**exponent

    # Choose a power where no artifical zero (due to rounding) needs to be
    # placed left of the decimal point.
    scale_symbols = {
        -4 : "p",
        -3 : "n",
        -2 : u"µ",
        -1 : "m",
        0 : "",
        1 : "K",
        2 : "M",
        3 : "G",
        4 : "T",
        5 : "P",
    }
    scale = 0

    while exponent < 0:
        scale -= 1
        exponent += 3

    # scale, exponent = divmod(exponent, 3)
    places_before_comma = exponent + 1
    places_after_comma = precision - places_before_comma
    while places_after_comma < 0:
        scale += 1
        exponent -= 3
        places_before_comma = exponent + 1
        places_after_comma = precision - places_before_comma
    value = mantissa * 10**exponent
    return u"%%.%df %%s%%s" % places_after_comma % (value, scale_symbols[scale], unit)


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
    perfometer_type, definition = perfometer

    if perfometer_type == "logarithmic":
        expression, median, exponent = definition
        value, unit = evaluate(expression, translated_metrics)
        color = get_color(expression)
        label = value_to_text(value, unit)
        stack = [ metricometer_logarithmic(value, median, exponent, color) ]

    elif perfometer_type == "linear":
        entry = []
        stack = [entry]

        # NOTE: This might be converted to a dict later.
        metrics_expressions, total_spec, label_expression = definition
        summed = 0.0

        for ex in metrics_expressions:
            value, unit = evaluate(ex, translated_metrics)
            summed += value

        if total_spec == None:
            total = summed
        else:
            total, unit = evaluate(total_spec, translated_metrics)

        for ex in metrics_expressions:
            value, unit = evaluate(ex, translated_metrics)
            color = get_color(ex)
            entry.append((100.0 * value / total, color))

        # Paint rest only, if it is positive and larger than one promille
        if total - summed > 0.001:
            entry.append((100.0 * (total - summed) / total, "#ffffff"))

        # Use unit of first metrics for output of sum. We assume that all
        # stackes metrics have the same unit anyway
        if label_expression:
            expr, unit = label_expression
            value, unit = evaluate(expr, translated_metrics)
            label = value_to_text(value, unit)
        else: # absolute
            unit = get_unit(metrics_expressions[0])
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




def page_pnp_template():
    # Beware! We run in unauthenticated context!!
    host_name        = html.var("host")
    service_desc     = html.var("service")
    perf_data_string = html.var("perfdata")
    check_command    = html.var("check_command")

    perf_data, check_command = parse_perf_data(perf_data_string, check_command)
    if not perf_data or not check_command:
        return

    translated_metrics = translate_metrics(perf_data, check_command)
    if not translated_metrics:
        return # check not supported

    graphs = get_graphs(translated_metrics)
    for graph in graphs:
        output_pnp_graph(graph, host_name, service_desc, translated_metrics)


def output_pnp_graph(graph, host_name, service_desc, translated_metrics):
    first_metric_info = metric_info[graph["metrics"][0][0]]

    title = graph.get("title")
    # If the graph does not provide a title then take the title of the
    # first (and possibly only) metric
    if title == None:
        title = first_metric_info["title"]

    vertical_label = graph.get("vertical_label")
    # If the graph does not provide a vertical label then take the unit
    # of the first metric
    if vertical_label == None:
        unit_name = first_metric_info["unit"]
        vertical_label = unit_info[unit_name]["title"]

    html.write("--vertical-label %s --title %s\n" % (
        quote_shell_string(vertical_label),
        quote_shell_string(title)))

    rrdgraph_commands = ""
    for metric_definition in graph["metrics"]:
        metric_name = metric_definition[0]
        line_type = metric_definition[1] # "line", "area", "stack"
        if line_type == "line":
            draw_type = "LINE"
            draw_stack = ""
        elif line_type == "area":
            draw_type = "AREA"
            draw_stack = ""
        elif line_type == "stack":
            draw_type = "AREA"
            draw_stack = ":STACK"

        mi = metric_info[metric_name]
        unit = unit_info[mi["unit"]]
        rrd = rrd_path(host_name, service_desc, translated_metrics[metric_name]["orig_name"])
        rrdgraph_commands += "DEF:%s=%s:1:MAX " % (metric_name, rrd)
        # TODO: Hier muss noch die Skalierung rein!!!
        rrdgraph_commands += "%s:%s%s:\"%s\"%s " % (draw_type, metric_name, mi["color"], ("%-20s" % mi["title"]), draw_stack)
        rrdgraph_commands += "GPRINT:%s:AVERAGE:\"avg\\: %%8.2lf %s\" "  % (metric_name, unit["symbol"].replace("%", "%%"))
        rrdgraph_commands += "GPRINT:%s:MAX:\"max\\: %%8.2lf %s\" "      % (metric_name, unit["symbol"].replace("%", "%%"))
        rrdgraph_commands += "GPRINT:%s:LAST:\"last\\: %%8.2lf %s\\n\" " % (metric_name, unit["symbol"].replace("%", "%%"))
        if line_type == "area":
            rrdgraph_commands += "LINE:%s%s " % (metric_name, render_color(darken_color(parse_color(mi["color"]), 0.2)))

    html.write(rrdgraph_commands + "\n")



def rrd_path(host_name, service_desc, varname):
    return "%s/%s/%s_%s.rrd" % (
        defaults.rrd_path,
        pnp_cleanup(host_name),
        pnp_cleanup(service_desc),
        pnp_cleanup(varname))


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
        return 1.0 - ((1.0 - x) * (1.0 - v))
    return tuple([ lighten(x, v) for x in rgb ])
