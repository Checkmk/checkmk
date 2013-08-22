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

import defaults
import os
import time

from lib import *

graph_size = 2000, 700

# Import helper functions from check_mk module prediction.py. Maybe we should
# find some more clean way some day for creating common Python code between
# Check_MK CCE and Multisite.
execfile(defaults.modules_dir + "/prediction.py")
rrd_path = defaults.rrd_path
rrdcached_socket = None
omd_root = None
try:
    omd_root = default.omd_root
    if omd_root:
        rrdcached_socket = omd_root + "/tmp/run/rrdcached.sock"
    else:
        try:
            rrdcached_socket = config.rrdcached_socket
        except:
            pass
except:
    pass

def page_graph():
    host = html.var("host")
    service = html.var("service")
    dsname = html.var("dsname")
    html.header(_("Prediction for %s - %s - %s") %
            (host, service, dsname),
            javascripts=["prediction"],
            stylesheets=["pages", "prediction"])

    # Get current value from perf_data via Livestatus
    current_value = \
       get_current_perfdata(host, service, dsname)

    dir = "%s/prediction/%s/%s/%s" % (
            defaults.var_dir, host, pnp_cleanup(service), pnp_cleanup(dsname))

    # Load all prediction information, sort by time of generation
    tg_name = html.var("timegroup")
    timegroup = None
    timegroups = []
    for f in os.listdir(dir):
        if f.endswith(".info"):
            tg_info = eval(file(dir + "/" + f).read())
            tg_info["name"] = f[:-5]
            timegroups.append(tg_info)
            if tg_info["name"] == tg_name:
                timegroup = tg_info

    timegroups.sort(cmp = lambda a,b: cmp(a["range"], b["range"]))
    if not timegroup:
        timegroup  = timegroups[0]

    choices = [ (tg_info["name"], tg_info["name"].title())
                for tg_info in timegroups ]

    html.begin_form("prediction")
    html.write(_("Show prediction for "))
    html.select("timegroup", choices, choices[0], onchange="document.prediction.submit();")
    html.hidden_fields()
    html.end_form()

    # Get prediction data
    tg_data = eval(file(dir + "/" + timegroup["name"]).read())
    swapped = swap_and_compute_levels(tg_data, timegroup)
    vertical_range = compute_vertical_range(swapped)
    legend = [
       ( "#000000", _("Reference") ),
       ( "#ffffff", _("OK area") ),
       ( "#ffff00", _("Warning area") ),
       ( "#ff0000", _("Critical area") ),
    ]
    if current_value != None:
        legend.append( ("#0000ff", _("Current value: %.2f") % current_value) )

    create_graph(timegroup["name"], graph_size, timegroup["range"], vertical_range, legend)

    if "levels_upper" in timegroup:
        render_dual_area(swapped["upper_warn"], swapped["upper_crit"], "#fff000", 0.4)
        render_area_reverse(swapped["upper_crit"], "#ff0000", 0.1)

    if "levels_lower" in timegroup:
        render_dual_area(swapped["lower_crit"], swapped["lower_warn"], "#fff000", 0.4)
        render_area(swapped["lower_crit"], "#ff0000", 0.1)

    vscala_low = vertical_range[0]
    vscala_high = vertical_range[1]
    vert_scala = compute_vertical_scala(vscala_low, vscala_high)
    time_scala = [ [timegroup["range"][0] + i*3600, "%02d:00" % i] for i in range(0, 25, 2) ]
    render_coordinates(vert_scala, time_scala);

    if "levels_lower" in timegroup:
        render_dual_area(swapped["average"], swapped["lower_warn"], "#ffffff", 0.5)
        render_curve(swapped["lower_warn"], "#e0e000", square=True)
        render_curve(swapped["lower_crit"], "#f0b0a0", square=True)

    if "levels_upper" in timegroup:
        render_dual_area(swapped["upper_warn"], swapped["average"], "#ffffff", 0.5)
        render_curve(swapped["upper_warn"], "#e0e000", square=True)
        render_curve(swapped["upper_crit"], "#f0b0b0", square=True)
    render_curve(swapped["average"], "#000000")
    render_curve(swapped["average"], "#000000")
    # render_curve(stack(swapped["average"], swapped["stdev"], -1),  "#008040")

    # Try to get current RRD data and render it also
    from_time, until_time = timegroup["range"]
    rrd_step, rrd_data = get_rrd_data(host, service, dsname, "MAX", from_time, until_time)
    render_curve(rrd_data, "#0000ff", 2)

    if current_value != None:
        rel_time = (time.time() - time.timezone) % timegroup["slice"]
        render_point(timegroup["range"][0] + rel_time, current_value, "#0000ff")

    html.footer()

vranges = [
 ( 'n', 1024.0**-3 ),
 ( 'u', 1024.0**-2 ),
 ( 'm', 1024.0**-1 ),
 ( '',  1024.0**0 ),
 ( 'K', 1024.0**1 ),
 ( 'M', 1024.0**2 ),
 ( 'G', 1024.0**3 ),
 ( 'T', 1024.0**4 ),
]

def compute_vertical_scala(low, high):
    m = max(abs(low), abs(high))
    for letter, factor in vranges:
        if m <= 15 * factor:
            break
    else:
        letter = 'P'
        factor = 1024.0**5

    v = 0
    vert_scala = []
    steps = (max(0, high) - min(0, low)) / factor
    if steps < 3:
        step = 0.2 * factor
    elif steps < 6:
        step = 0.5 * factor
    else:
        step = factor

    while v <= max(0, high):
        vert_scala.append( [v, "%.1f%s" % (v / factor, letter)] )
        v += step

    v = -factor
    while v >= min(0, low):
        vert_scala = [ [v, "%.1f%s" % (v / factor, letter)] ] + vert_scala
        v -= step

    return vert_scala

def get_current_perfdata(host, service, dsname):
    perf_data = html.live.query_value("GET services\nFilter: host_name = %s\nFilter: description = %s\nColumns: perf_data" % (
            host, service))
    for part in perf_data.split():
        name, rest = part.split("=")
        if name == dsname:
            return float(rest.split(";")[0])

# Compute check levels from prediction data and check parameters
def swap_and_compute_levels(tg_data, tg_info):
    columns = tg_data["columns"]
    swapped = dict([ (c, []) for c in columns])
    for step in tg_data["points"]:
        row = dict(zip(columns, step))
        for k, v in row.items():
            swapped[k].append(v)
        if row["average"] != None and row["stdev"] != None:
            upper, lower = compute_levels(tg_info, row["average"], row["stdev"])
            if upper[0] != None:
                swapped.setdefault("upper_warn", []).append(upper[0])
                swapped.setdefault("upper_crit", []).append(upper[1])
            if lower[0] != None:
                swapped.setdefault("lower_warn", []).append(lower[0])
                swapped.setdefault("lower_crit", []).append(lower[1])
        else:
            swapped.setdefault("upper_warn", []).append(0)
            swapped.setdefault("upper_crit", []).append(0)
            swapped.setdefault("lower_warn", []).append(0)
            swapped.setdefault("lower_crit", []).append(0)

    return swapped

def stack(apoints, bpoints, scale):
    return [ a + scale * b for (a,b) in zip(apoints, bpoints) ]


# Compute levels according to check parameters. Beware: this
# code is duplicated from modules/prediction.py. Sorry for this
# copy&paste. This was neccessary since there is currently no common
# code between Check_MK CCE and Multisite.
def compute_levels(params, ref_value, stdev):
    levels = []
    for what, sig in [ ( "upper", 1 ), ( "lower", -1 )]:
        p = "levels_" + what
        if p in params:
            how, (warn, crit) = params[p]
            if how == "absolute":
                levels.append((ref_value + (sig * warn), ref_value + (sig * crit)))

            elif how == "relative":
                levels.append((ref_value + sig * (ref_value * warn / 100),
                               ref_value + sig * (ref_value * crit / 100)))

            else: #  how == "stdev":
                levels.append((ref_value + sig * (stdev * warn),
                              ref_value + sig * (stdev * crit)))
        else:
            levels.append((None, None))
    return levels

def compute_vertical_range(swapped):
    mmin, mmax = 0.0, 0.0
    for name, points in swapped.items():
        mmax = max(mmax, max(points)) or 0.0 # convert None into 0.0
        mmin = min(mmin, min(points)) or 0.0
    return mmin, mmax

def create_graph(name, size, range, v_range, legend):
    html.write('<table class=prediction><tr><td>')
    html.write('<canvas class=prediction id="content_%s" style="width: %dpx; height: %dpx;" width=%d height=%d></canvas>' % (
       name, size[0]/2, size[1]/2, size[0], size[1]))
    html.write('</td></tr><tr><td class=legend>')
    for color, title in legend:
        html.write('<div class=color style="background-color: %s"></div><div class=entry>%s</div>' % (
                    color, title))
    html.write('</div></td></tr></table>')
    html.javascript('create_graph("content_%s", %.4f, %.4f, %.4f, %.4f);' % (
                 name, range[0], range[1], v_range[0], v_range[1]))

def render_coordinates(v_scala, t_scala):
    html.javascript('render_coordinates(%r, %r);' % (v_scala, t_scala))


def render_curve(points, color, width=1, square=False):
    html.javascript('render_curve(%r, %r, %d, %d);' % (
              points, color, width, square and 1 or 0))

def render_point(t, v, color):
    html.javascript('render_point(%r, %r, %r);' % (t, v, color))

def render_area(points, color, alpha=1.0):
    html.javascript('render_area(%r, %r, %f);' % (points, color, alpha))

def render_area_reverse(points, color, alpha=1.0):
    html.javascript('render_area_reverse(%r, %r, %f);' % (points, color, alpha))

def render_dual_area(lower_points, upper_points, color, alpha=1.0):
    html.javascript('render_dual_area(%r, %r, %r, %f);' % (lower_points, upper_points, color, alpha))
