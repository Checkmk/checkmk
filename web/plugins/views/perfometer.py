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
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

# Painters for Perf-O-Meter
import math
import metrics

perfometers = {}

# TODO: Umbau: alle Funktionen perfometer_.. geben eine logische Struktur
# zurück.
# perfometer_td() -> perfometer_segment() ergibt (breite_in_proz, farbe)
# Ein perfometer ist eine Liste von Listen.
# [ [segment, segment, segment], [segment, segment] ] --> horizontal gespaltet.
# Darin die vertikalen Balken.

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
    style = ["width: %d%%;" % int(float(perc)), "background-color: %s" % color]
    return html.render_td('', class_="inner", style=style)


# render the perfometer table
# data is expected to be a list of tuples [(perc, color), (perc2, color2), ...]
def render_perfometer(data):
    tds = HTML().join(render_perfometer_td(percentage, color) for percentage, color in data)
    return html.render_table(html.render_tr(tds))


# Paint linear performeter with one value
def perfometer_linear(perc, color):
    return render_perfometer([(perc, color), (100-perc, "white")])


# Paint logarithm with base 10, half_value is being
# displayed at 50% of the width
def perfometer_logarithmic(value, half_value, base, color):
    return render_metricometer([metrics.metricometer_logarithmic(value, half_value, base, color)])


# prepare the rows for logarithmic perfometers (left or right)
def calculate_half_row_logarithmic(left_or_right, value, color, half_value, base):
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
        if left_or_right == "right":
            return [(pos, color), (50 - pos, "white")]
        else:
            return [(50 - pos, "white"), (pos, color)]


# Dual logarithmic Perf-O-Meter
def perfometer_logarithmic_dual(value_left, color_left, value_right, color_right, half_value, base):
    data = []
    data.extend(calculate_half_row_logarithmic("left", value_left, color_left, half_value, base))
    data.extend(calculate_half_row_logarithmic("right", value_right, color_right, half_value, base))
    return render_perfometer(data)


def perfometer_logarithmic_dual_independent\
    (value_left, color_left, half_value_left, base_left, value_right, color_right, half_value_right, base_right):
    data = []
    data.extend(calculate_half_row_logarithmic("left", value_left, color_left, half_value_left, base_left))
    data.extend(calculate_half_row_logarithmic("right", value_right, color_right, half_value_right, base_right))
    return render_perfometer(data)


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
        title = None
        translated_metrics = metrics.translate_metrics(perf_data, check_command)
        if translated_metrics: # definition for this check type exists
            perfometer_definitions = list(metrics.get_perfometers(translated_metrics))
            if perfometer_definitions:
                title, h = render_metrics_perfometer(perfometer_definitions[0], translated_metrics)

        # Legacy Perf-O-Meters: find matching Perf-O-Meter function
        if title == None:
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

    content = html.render_div(HTML(h), class_=["content"]) \
            + html.render_div(title, class_=["title"]) \
            + html.render_img(src="images/perfometer-bg.png", class_=["glass"])

    # pnpgraph_present: -1 means unknown (path not configured), 0: no, 1: yes
    if display_options.enabled(display_options.X) \
       and row["service_pnpgraph_present"] != 0:
        if metrics.cmk_graphs_possible():
            url = new_graphing_url(row, "service")
        else:
            url = pnp_url(row, "service")
        disabled = False
    else:
        url = "javascript:void(0)"
        disabled = True

    return "perfometer" + stale_css, \
        html.render_a(content=content, href=url, title=title,
                      class_=["disabled" if disabled else None])


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
    h = HTML().join(map(render_perfometer, stack))
    if len(stack) == 2:
        h = html.render_div(h, class_="stacked")
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
