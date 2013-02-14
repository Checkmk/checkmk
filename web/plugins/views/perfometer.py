#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2013             mk@mathias-kettner.de |
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

perfometers = {}

# Helper functions for perfometers
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
    value = float(value)
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

    return "<table><tr>" + \
      perfometer_td(pos, color) + \
      perfometer_td(100 - pos, "white") + \
      "</tr></table>"


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


def number_human_readable(n, precision=1, unit="B"):
    n = float(n)
    f = "%." + str(precision) + "f"
    if abs(n) > 1024 * 1024 * 1024:
        return (f + "G%s") % (n / (1024.0 * 1024 * 1024), unit)
    elif abs(n) > 1024 * 1024:
        return (f + "M%s") % (n / (1024.0 * 1024), unit)
    elif abs(n) > 1024:
        return (f + "k%s") % (n / 1024.0, unit)
    else:
        return (f + "%s") % (n, unit)

def age_human_readable(secs):
    if secs < 240:
        return "%d sec" % secs
    mins = secs / 60
    if mins < 240:
        return "%d min" % mins
    hours = mins / 60
    if hours < 48:
        return "%d hours" % hours
    days = hours / 24
    return "%d days" % days


def paint_perfometer(row):
    perfstring = unicode(row["service_perf_data"].strip())
    if not perfstring:
        return "", ""

    parts = perfstring.split()
    # Try if check command is appended to performance data
    # in a PNP like style
    if parts[-1].startswith("[") and parts[-1].endswith("]"):
        check_command = parts[-1][1:-1]
        del parts[-1]
    else:
        check_command = row["service_check_command"]

    # Strip away arguments like in "check_http!-H mathias-kettner.de"
    check_command = check_command.split("!")[0]

    # Find matching perf-o-meter function
    perf_painter = perfometers.get(check_command)
    if not perf_painter:
        return "", ""

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
        perf_data = None
    if not perf_data:
        return "", ""

    try:
        title, h = perf_painter(row, check_command, perf_data)
        content =  '<div class=content>%s</div>' % h
        content += '<div class=title>%s</div>' % title
        content += '<img class=glass src="images/perfometer-bg.png">'

        # pnpgraph_present: -1 means unknown (path not configured), 0: no, 1: yes
        if 'X' in html.display_options and \
           row["service_pnpgraph_present"] != 0:
            return "perfometer", ('<a href="%s">%s</a>' % (pnp_url(row, "service"), content))
        else:
            return "perfometer", content


    except Exception, e:
        if config.debug:
            raise
        return "perfometer", ("invalid data: %s" % e)

multisite_painters["perfometer"] = {
    "title" : _("Service Perf-O-Meter"),
    "short" : _("Perf-O-Meter"),
    "columns" : [ "service_perf_data", "service_state",
                  "service_check_command", "service_pnpgraph_present", "service_plugin_output" ],
    "paint" : paint_perfometer
}

load_web_plugins("perfometer", globals())
