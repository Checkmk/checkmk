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

# Painters for Perf-O-Meter
import math
import metrics

perfometers = {}

# TODO: Umbau: alle Funktionen perfometer_.. geben eine logische Struktur
# zurück.
# perfometer_td() -> perfometer_segment() ergebit (breite_in_proz, farbe)
# Ein perfometer ist eine Liste von Listen.
# [ [segment, segment, segment], [segment, segment] ] --> horizontal gespaltet.
# Darin die vertikalen Balken.

#.
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

def perfometer_td(perc, color):
    return '<td class="inner" style="background-color: %s; ' \
           'width: %d%%;"></td>' % (color, int(float(perc)))

# Paint linear performeter with one value
def perfometer_linear(perc, color):
    return "<table><tr>" + \
        perfometer_td(perc, color) + \
        perfometer_td(100 - perc, "white") + \
        "</tr></table>"

# Paint logarithm with base 10, half_value is being
# displayed at 50% of the width
def perfometer_logarithmic(value, half_value, base, color):
    return render_metricometer([metrics.metricometer_logarithmic(value, half_value, base, color)])


# Dual logarithmic Perf-O-Meter
def perfometer_logarithmic_dual(value_left, color_left, value_right, color_right, half_value, base):
    result = '<table><tr>'
    for where, value, color in [
        ("left", value_left, color_left),
        ("right", value_right, color_right) ]:
        value = float(value)
        if value == 0.0:
            pos = 0
        else:
            half_value = float(half_value)
            h = math.log(half_value, base) # value to be displayed at 50%
            pos = 25 + 10.0 * (math.log(value, base) - h)
            if pos < 1:
                pos = 1
            if pos > 49:
                pos = 49

        if where == "right":
            result += perfometer_td(pos, color) + \
                 perfometer_td(50 - pos, "white")
        else:
            result += perfometer_td(50 - pos, "white") + \
                 perfometer_td(pos, color)

    return result + '</tr></table>'

def perfometer_logarithmic_dual_independent\
    (value_left, color_left, half_value_left, base_left, value_right, color_right, half_value_right, base_right):
    result = '<table><tr>'
    for where, value, color, half_value, base in [
        ("left", value_left, color_left, half_value_left, base_left),
        ("right", value_right, color_right, half_value_right, base_left) ]:
        value = float(value)
        if value == 0.0:
            pos = 0
        else:
            half_value = float(half_value)
            h = math.log(half_value, base) # value to be displayed at 50%
            pos = 25 + 10.0 * (math.log(value, base) - h)
            if pos < 1:
                pos = 1
            if pos > 49:
                pos = 49

        if where == "right":
            result += perfometer_td(pos, color) + \
                 perfometer_td(50 - pos, "white")
        else:
            result += perfometer_td(50 - pos, "white") + \
                 perfometer_td(pos, color)

    return result + '</tr></table>'


def paint_perfometer(row):
    perf_data_string = unicode(row["service_perf_data"].strip())
    if not perf_data_string:
        return "", ""

    perf_data, check_command = metrics.parse_perf_data(perf_data_string, row["service_check_command"])
    if not perf_data:
        return "", ""

    if is_stale(row):
        stale_css = " stale"
    else:
        stale_css = ""

    try:
        # Try new metrics module
        translated_metrics = metrics.translate_metrics(perf_data, check_command)
        if translated_metrics: # definition for this check type exists
            perfometer_definitions = list(metrics.get_perfometers(translated_metrics))
            if perfometer_definitions:
                title, h = render_metrics_perfometer(perfometer_definitions[0], translated_metrics)
            else:
                return "", ""

        # Legacy Perf-O-Meters: find matching Perf-O-Meter function
        else:
            perf_painter = perfometers.get(check_command)
            if not perf_painter:
                return "", ""

            title, h = perf_painter(row, check_command, perf_data)
            if not h:
                return "", ""
            # Test code for optically detecting old-style Perf-O-Meters
            if config.debug:
                title = '{ ' + title + ' }'

    except Exception, e:
        if config.debug:
            raise
        return "perfometer", ("invalid data: %s" % e)

    content =  '<div class=content>%s</div>' % h
    content += '<div class=title>%s</div>' % title
    content += '<img class=glass src="images/perfometer-bg.png">'

    # pnpgraph_present: -1 means unknown (path not configured), 0: no, 1: yes
    if 'X' in html.display_options and \
       row["service_pnpgraph_present"] != 0:
        return "perfometer" + stale_css, ('<a href="%s">%s</a>' % (pnp_url(row, "service"), content))
    else:
        return "perfometer" + stale_css, content


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
        raise MKGeneralException(_("Invalid Perf-O-Meter definition %r: only one or two entries are allowed") % stack)

    h = ""
    if len(stack) == 2:
        h += '<div class="stacked">'

    for entry in stack:
        h += '<table><tr>'
        for percentage, color in entry:
            h += perfometer_td(percentage, color)
        h += "</tr></table>"

    if len(stack) == 2:
        h += '</div>'
    return h

# Compute logarithmic Perf-O-Meter


def render_metrics_perfometer(perfometer, translated_metrics):
    label, stack = metrics.build_perfometer(perfometer, translated_metrics)
    return label, render_metricometer(stack)



multisite_painters["perfometer"] = {
    "title" : _("Service Perf-O-Meter"),
    "short" : _("Perf-O-Meter"),
    "columns" : [ "service_perf_data", "service_state",
                  "service_check_command", "service_pnpgraph_present", "service_plugin_output" ],
    "paint" : paint_perfometer,
    "sorter" : "svc_perf_val01",
    "printable" : "perfometer", # Special rendering in PDFs
}

load_web_plugins("perfometer", globals())
