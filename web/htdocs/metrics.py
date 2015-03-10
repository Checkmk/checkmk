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
# unit_name:          The ID of a unit, e.g. "%"
# unit:               The definition-dict of a unit like in unit_info

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
            unit_name = value[i:]
            value = value[:i]
            perf_data.append((varname, value, unit_name, warn, crit, min, max))
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
def evaluate(expression, translated_metrics):
    if type(expression) in (float, int) or "," not in expression:
        return evaluate_literal(expression, translated_metrics)
    else:
        if "#" in expression:
            expression, explicit_color = expression.rsplit("#", 1) # drop appended color information
        else:
            explicit_color = None
        value, unit, color = evaluate_rpn(expression, translated_metrics)
        if explicit_color:
            color = "#" + explicit_color
        return value, unit, color


# TODO: Do real unit computation, detect non-matching units
rpn_operators = {
    "+"  : lambda a, b: ((a[0] +  b[0]),                a[1],         choose_operator_color(a[2], b[2])),
    "-"  : lambda a, b: ((a[0] -  b[0]),                a[1],         choose_operator_color(a[2], b[2])),
    "*"  : lambda a, b: ((a[0] *  b[0]),                a[1],         choose_operator_color(a[2], b[2])),
    "/"  : lambda a, b: ((a[0] /  b[0]),                "",           choose_operator_color(a[2], b[2])),
    ">"  : lambda a, b: ((a[0] >  b[0] and 1.0 or 0.0), "",           "#000000"),
    "<"  : lambda a, b: ((a[0] <  b[0] and 1.0 or 0.0), "",           "#000000"),
    ">=" : lambda a, b: ((a[0] >= b[0] and 1.0 or 0.0), "",           "#000000"),
    "<=" : lambda a, b: ((a[0] <= b[0] and 1.0 or 0.0), "",           "#000000"),
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
            stack = stack[:-2] + [ rpn_operators[operator_name](op1, op2) ]
        else:
            stack.append(evaluate_literal(operator_name, translated_metrics))

    if len(stack) != 1:
        raise MKGeneralException("Syntax error in expression '%s': too many operands left" % expression)

    return stack[0]


def evaluate_literal(expression, translated_metrics):
    if type(expression) == int:
        return expression, "count", None

    elif type(expression) == float:
        return expression, None, None

    elif expression[0].isdigit() or expression[0] == '-':
        return float(expression), "", None

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
        maxvalue = translated_metrics[varname]["scalar"]["max"]
        if maxvalue != 0:
           value = 100.0 * float(value) / maxvalue
        else:
           value = 0.0
        unit = unit_info["%"]

    else:
        unit = translated_metrics[varname]["unit"]

    color = metric_info[varname]["color"]
    return value, unit, color


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
        else:
            required = [] # TODO: logarithmic, etc.
        if "label" in perfometer:
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
def physical_precision(v, precision, unit_symbol):
    if v == 0:
        return "%%.%df" % (precision - 1) % v
    elif v < 0:
        return "-" + physical_precision(-v, precision, unit_symbol)

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
    return u"%%.%df %%s%%s" % places_after_comma % (value, scale_symbols[scale], unit_symbol)


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
        if perfometer["type"] == "linear":
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
            if "label" in perfometer:
                expr, unit_name = perfometer["label"]
                value, unit, color = evaluate(expr, translated_metrics)
                if unit_name:
                    unit = unit_info[unit_name]
                label = unit["render"](summed)
            else: # absolute
                value, unit, color = evaluate(metrics_expressions[0], translated_metrics)
                label = unit["render"](summed)

            return label, stack



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

    graphs = get_graphs(translated_metrics)

    # Collect output in string. In case of an exception to not output
    # any definitions
    output = ""
    for graph in graphs:
        output += render_pnp_graph(graph, translated_metrics)
    html.write(output)



def render_pnp_graph(graph, translated_metrics):

    graph_title = None
    vertical_label = None

    rrdgraph_commands = ""

    # Define one RRD variable for each of the available metrics.
    # Note: We need to use the original name, not the translated one.
    for var_name, metrics in translated_metrics.items():
        rrd = "$RRDBASE$_" + pnp_cleanup(metrics["orig_name"]) + ".rrd"
        scale = metrics["scale"]
        if scale != 1.0:
            rrdgraph_commands += "DEF:%s_UNSCALED=%s:1:MAX " % (var_name, rrd)
            rrdgraph_commands += "CDEF:%s=%s_UNSCALED,%f,* " % (var_name, var_name, scale)

        else:
            rrdgraph_commands += "DEF:%s=%s:1:MAX " % (var_name, rrd)

    # Compute width of columns in case of mirrored legend

    mirror_legend = graph.get("mirror_legend")
    total_width = 89 # characters
    left_width = max([len(_("Average")), len(_("Maximum")), len(_("Last"))]) + 2
    column_width = (total_width - left_width) / len(graph["metrics"]) - 2

    # Now add areas and lines to the graph
    graph_metrics = []

    for nr, metric_definition in enumerate(graph["metrics"]):
        metric_name = metric_definition[0]
        line_type = metric_definition[1] # "line", "area", "stack"

        # Optional title, especially for derived values
        if len(metric_definition) >= 3:
            title = metric_definition[2]
        else:
            title = ""

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
            metric_name = "DERIVED%d" % nr

        else:
            mi = metric_info[metric_name]
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
            right_pad = " " * (left_width - len(title))
        commands += "%s:%s%s:\"%s%s\"%s " % (draw_type, metric_name, color, title, right_pad, draw_stack)
        if line_type == "area":
            commands += "LINE:%s%s " % (metric_name, render_color(darken_color(parse_color(color), 0.2)))

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
                    rrdgraph_commands += "GPRINT:%%s:%%s:\"%%%%%d.2lf%%s\" " % column_width % (metric_name, what, unit_symbol)
            rrdgraph_commands += "COMMENT:\"\\n\" "
    else:
        for metric_name, unit_symbol, commands in graph_metrics:
            rrdgraph_commands += commands
            rrdgraph_commands += "GPRINT:%s:AVERAGE:\"%%8.2lf%s %s\" "  % (metric_name, unit_symbol, _("average"))
            rrdgraph_commands += "GPRINT:%s:MAX:\"%%8.2lf%s %s\" "          % (metric_name, unit_symbol, _("max"))
            rrdgraph_commands += "GPRINT:%s:LAST:\"%%8.2lf%s %s\\n\" "     % (metric_name, unit_symbol, _("last"))




    # Now compute the arguments for the command line of rrdgraph
    rrdgraph_arguments = ""

    graph_title = graph.get("title", graph_title)
    vertical_label = graph.get("vertical_label", vertical_label)

    rrdgraph_arguments += "--vertical-label %s --title %s -L 4" % (
        quote_shell_string(vertical_label),
        quote_shell_string(graph_title))

    if "range" in graph:
        rrdgraph_arguments += " -l %f -u %f" % graph["range"]

    # Some styling options, currently hardcoded
    rrdgraph_arguments += " --color MGRID\"#cccccc\" --color GRID\"#dddddd\" --width=600";
    rrdgraph_arguments += "\n"

    return rrdgraph_arguments + rrdgraph_commands


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

def mix_colors(a, b):
    return tuple([
       (ca + cb) / 2.0
       for (ca, cb)
       in zip(a, b)
    ])
