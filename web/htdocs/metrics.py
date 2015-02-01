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
    global perfometer_info ; perfometer_info = []
    global check_metrics   ; check_metrics   = {}
    load_web_plugins("metrics", globals())
    loaded_with_language = current_language


# Convert Ascii-based performance data as output from a check plugin
# into floating point numbers, do scaling if neccessary.
# Simple example for perf_data: [(u'temp', u'48', u'', u'70', u'80', u'', u'')]
# Result for this example:
# { "temp" : "value" : 48.0, "warn" : 70.0, "crit" : 80.0 }
def translate_metrics(check_command, perf_data):
    if check_command not in check_metrics:
        return None

    cm = check_metrics[check_command]

    translated = {}
    for entry in perf_data:
        varname = entry[0]
        translation_entry = cm.get(varname, {})
        metrics_name = translation_entry.get("name", varname)
        # TODO: scaling
        new_entry = {
            "value" : float(entry[1]),
        }
        new_entry.update(metric_info[metrics_name])
        new_entry["unit"] = unit_info[new_entry["unit"]]
        translated[metrics_name] = new_entry
        # TODO: warn, crit, min, max
        # if entry[2]:
        #     # TODO: lower and upper levels
        #     translate_metrics[metrics_name]["warn"] = float(entry[2])
    return translated


def get_perfometers(metrics):
    for perfometer in perfometer_info:
        if perfometer_possible(perfometer, metrics):
            yield perfometer


def perfometer_possible(perfometer, metrics):
    perf_type, perf_args = perfometer
    if perf_type == "single_logarithmic":
        required = [ perf_args[0] ]
    elif perf_type == "stacked":
        required = perf_args[0]

    for req in required:
        if req not in metrics:
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
