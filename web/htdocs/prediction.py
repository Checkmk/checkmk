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

import os
import time

import cmk.paths
import config
import sites
from lib import *
import cmk.store as store

try:
    import simplejson as json
except ImportError:
    import json


graph_size = 2000, 700


def page_graph():
    host    = html.var("host")
    service = html.var("service")
    dsname  = html.var("dsname")

    html.header(_("Prediction for %s - %s - %s") %
            (host, service, dsname),
            javascripts=["prediction"],
            stylesheets=["pages", "prediction"])

    # Get current value from perf_data via Livestatus
    current_value = get_current_perfdata(host, service, dsname)

    dir = "%s/prediction/%s/%s/%s" % (
            cmk.paths.var_dir, host, pnp_cleanup(service), pnp_cleanup(dsname))

    if not os.path.exists(dir):
        raise MKGeneralException(_("There is currently no prediction information "
                                   "available for this service."))

    # Load all prediction information, sort by time of generation
    tg_name = html.var("timegroup")
    timegroup = None
    timegroups = []
    now = time.time()
    for f in os.listdir(dir):
        file_path = dir + "/" + f
        if not f.endswith(".info"):
            continue

        tg_info = store.load_data_from_file(dir + "/" + f)
        if tg_info == None:
            continue

        tg_info["name"] = f[:-5]
        timegroups.append(tg_info)
        if tg_info["name"] == tg_name or \
            (tg_name == None and now >= tg_info["range"][0] and now <= tg_info["range"][1]):
            timegroup = tg_info
            tg_name = tg_info["name"]

    timegroups.sort(cmp = lambda a,b: cmp(a["range"][0], b["range"][0]))

    choices = [ (tg_info["name"], tg_info["name"].title())
                for tg_info in timegroups ]

    if not timegroup:
        if timegroups:
            timegroup  = timegroups[0]
            tg_name = choices[0][0]
        else:
            raise MKGeneralException(_("Missing prediction information."))

    html.begin_form("prediction")
    html.write(_("Show prediction for "))
    html.dropdown("timegroup", choices, deflt=tg_name, onchange="document.prediction.submit();")
    html.hidden_fields()
    html.end_form()

    # Get prediction data
    path = dir + "/" + timegroup["name"]
    tg_data = store.load_data_from_file(path)
    if tg_data == None:
        raise MKGeneralException(_("Missing prediction data."))

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

    # Try to get current RRD data and render it also
    from_time, until_time = timegroup["range"]
    now = time.time()
    if now >= from_time and now <= until_time:
        if time.daylight:
            tz_offset = time.altzone
        else:
            tz_offset = time.timezone
        rrd_step, rrd_data = get_rrd_data(host, service, dsname, "MAX", from_time, until_time)
        render_curve(rrd_data, "#0000ff", 2)
        if current_value != None:
            rel_time = (now - tz_offset) % timegroup["slice"]
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
        if m <= 99 * factor:
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
    elif steps > 50:
        step = 5 * factor
    elif steps > 20:
        step = 2 * factor
    else:
        step = factor

    while v <= max(0, high):
        vert_scala.append( [v, "%.1f%s" % (v / factor, letter)] )
        v += step

    v = -factor
    while v >= min(0, low):
        vert_scala = [ [v, "%.1f%s" % (v / factor, letter)] ] + vert_scala
        v -= step

    # Remove trailing ".0", if that is present for *all* entries
    for entry in vert_scala:
        if not entry[1].endswith(".0"):
            break
    else:
        vert_scala = [ [e[0],e[1][:-2]] for e in vert_scala ]

    return vert_scala


def get_current_perfdata(host, service, dsname):
    perf_data = sites.live().query_value(
                    "GET services\nFilter: host_name = %s\nFilter: description = %s\n"
                    "Columns: perf_data" % (lqencode(host), lqencode(service)))

    for part in perf_data.split():
        name, rest = part.split("=")
        if name == dsname:
            return float(rest.split(";")[0])


# Fetch RRD historic metrics data of a specific service. returns a tuple
# of (step, [value1, value2, ...])
# IMPORTANT: Until we have a central library, keep this function in sync with
# the function get_rrd_data() from modules/prediction.py.
def get_rrd_data(hostname, service_description, varname, cf, fromtime, untiltime):
    step = 1
    rpn = "%s.%s" % (varname, cf.lower()) # "MAX" -> "max"
    query = "GET services\n" \
          "Columns: rrddata:m1:%s:%d:%d:%d\n" \
          "Filter: host_name = %s\n" \
          "Filter: description = %s\n" % (
             rpn, fromtime, untiltime, step,
             lqencode(hostname), lqencode(service_description))

    try:
        response = sites.live().query_row(query)[0]
    except Exception, e:
        if config.debug:
            raise
        raise MKGeneralException("Cannot get historic metrics via Livestatus: %s" % e)

    if not response:
        raise MKGeneralException("Got no historic metrics")

    real_fromtime, real_untiltime, step = response[:3]
    values = response[3:]
    return step, values


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
    return compute_level(params, ref_value, stdev, "levels_upper", 1), \
           compute_level(params, ref_value, stdev, "levels_lower", -1)


def compute_level(params, ref_value, stdev, param, sig):
    if param not in params:
        return None, None

    how, (warn, crit) = params[param]
    if how == "absolute":
        levels = (ref_value + (sig * warn),
                  ref_value + (sig * crit))

    elif how == "relative":
        levels = (ref_value + sig * (ref_value * warn / 100),
                  ref_value + sig * (ref_value * crit / 100))

    else: #  how == "stdev":
        levels = (ref_value + sig * (stdev * warn),
                  ref_value + sig * (stdev * crit))

    if param == "levels_upper" and "levels_upper_min" in params:
        limit_warn, limit_crit = params["levels_upper_min"]
        levels = (max(limit_warn, levels[0]),
                  max(limit_crit, levels[1]))

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
    html.javascript('render_coordinates(%s, %s);' % (json.dumps(v_scala), json.dumps(t_scala)))


def render_curve(points, color, width=1, square=False):
    html.javascript('render_curve(%s, %s, %d, %d);' % (
              json.dumps(points), json.dumps(color), width, square and 1 or 0))

def render_point(t, v, color):
    html.javascript('render_point(%s, %s, %s);' % (json.dumps(t), json.dumps(v), json.dumps(color)))

def render_area(points, color, alpha=1.0):
    html.javascript('render_area(%s, %s, %f);' % (json.dumps(points), json.dumps(color), alpha))

def render_area_reverse(points, color, alpha=1.0):
    html.javascript('render_area_reverse(%s, %s, %f);' %
        (json.dumps(points), json.dumps(color), alpha))

def render_dual_area(lower_points, upper_points, color, alpha=1.0):
    html.javascript('render_dual_area(%s, %s, %s, %f);' %
        (json.dumps(lower_points), json.dumps(upper_points), json.dumps(color), alpha))
