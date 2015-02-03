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
# perf_data_string: Raw performance data as sent by the core, e.g "foor=17M;1;2;4;5"
# perf_data:        Split performance data, e.g. [("foo", "17", "M", "1", "2", "4", "5")]
# translated_metrics: Completely parsed and translated into metrics, e.g. { "foo" : { "value" : 17.0, "unit" : { "render" : ... }, ... } }


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


# Convert Ascii-based performance data as output from a check plugin
# into floating point numbers, do scaling if neccessary.
# Simple example for perf_data: [(u'temp', u'48', u'', u'70', u'80', u'', u'')]
# Result for this example:
# { "temp" : "value" : 48.0, "warn" : 70.0, "crit" : 80.0, "unit" : { ... } }
def translate_metrics(check_command, perf_data):
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
            "value"     : float(entry[1]) * scale,
            "orig_name" : varname,
            "scalar"    : {},
        }

        # Add warn, crit, min, max
        for index, key in [ (3, "warn"), (4, "crit"), (5, "min"), (6, "max") ]:
            if len(entry) < index + 1:
                break
            elif entry[index]:
                try:
                    value = float(entry[index])
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
        #     translate_metrics[metric_name]["warn"] = float(entry[2])
    return translated_metrics


# e.g. "fs_used:max"    -> 12.455
# e.g. "fs_used(%)"     -> 17.5
# e.g. "fs_used:max(%)" -> 100.0
def evaluate(expression, translated_metrics):
    if type(expression) in (int, float):
        return expression

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
        value = value / translated_metrics[varname]["scalar"]["max"] * 100.0

    return value

# e.g. "fs_used:max(%)" -> "fs_used"
def get_name(expression):
    if expression.endswith("(%)"):
        expression = expression[:-3]
    return expression.split(":")[0]

def get_color(expression):
    return metric_info[get_name(expression)]["color"]

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
    elif perf_type == "stacked":
        required = perf_args[0]
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


def page_pnp_template():
    # Beware! We run in unauthenticated context!!
    host_name        = html.var("host")
    service_desc     = html.var("service")
    perf_data_string = html.var("perfdata")
    check_command    = html.var("check_command")

    perf_data, check_command = parse_perf_data(perf_data_string, check_command)
    if not perf_data or not check_command:
        return

    translated_metrics = translate_metrics(check_command, perf_data)
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
        rrdgraph_commands += "%s:%s%s:\"%s\"%s " % (draw_type, metric_name, mi["color"], ("%-20s" % mi["title"]), draw_stack)
        rrdgraph_commands += "GPRINT:%s:AVERAGE:\"avg\\: %%8.2lf %s\" "  % (metric_name, unit["symbol"].replace("%", "%%"))
        rrdgraph_commands += "GPRINT:%s:MAX:\"max\\: %%8.2lf %s\" "      % (metric_name, unit["symbol"].replace("%", "%%"))
        rrdgraph_commands += "GPRINT:%s:LAST:\"last\\: %%8.2lf %s\\n\" " % (metric_name, unit["symbol"].replace("%", "%%"))
        if line_type == "area":
            rrdgraph_commands += "LINE:%s%s " % (metric_name, render_color(darken_color(parse_color(mi["color"]), 0.2)))

    html.write(rrdgraph_commands + "\n")


# $def[1] = "DEF:var1=$RRDFILE[1]:$DS[1]:MAX ";
# $def[1] .= "AREA:var1#2080ff:\"Temperature\:\" ";
# $def[1] .= "GPRINT:var1:LAST:\"%2.0lfC\" ";
# $def[1] .= "LINE1:var1#000080:\"\" ";
# $def[1] .= "GPRINT:var1:MAX:\"(Max\: %2.0lfC,\" ";
# $def[1] .= "GPRINT:var1:AVERAGE:\"Avg\: %2.0lfC)\" ";

def rrd_path(host_name, service_desc, varname):
    return "%s/%s/%s_%s.rrd" % (
        defaults.rrd_path,
        pnp_cleanup(host_name),
        pnp_cleanup(service_desc),
        pnp_cleanup(varname))



    html.write(' --vertical-label \"Celsius\"  -l 0 -u 40 --title \"Temperature $servicedesc\" \n')
    html.write(
'DEF:var1=/opt/omd/foo/bar/test.rrd:temp:MAX '
'AREA:var1#2080ff:\"Temperature\:\" '
'GPRINT:var1:LAST:\"%2.0lfC\" '
'LINE1:var1#000080:\"\" '
'GPRINT:var1:MAX:\"(Max\: %2.0lfC,\" '
'GPRINT:var1:AVERAGE:\"Avg\: %2.0lfC)\"\n')


# "#ff0080" -> (1.0, 0.0, 0.5)
def parse_color(color_string):
    return tuple([ int(color_string[a:a+2], 16) / 255.0 for a in (1,3,5) ])

def render_color(rgb):
    return "#%02x%02x%02x" % (
       int(rgb[0] * 255),
       int(rgb[1] * 255),
       int(rgb[2] * 255),)

# Make a color darker. v ranges from 0 (not darker) to 1 (black)
def darken_color(rgb, v):
    def darken(x, v):
        return x * (1.0 - v)
    return tuple([ darken(x, v) for x in rgb ])
