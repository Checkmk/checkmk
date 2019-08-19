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

from __future__ import division
import os
import time
import json

import livestatus
import cmk.utils.paths
import cmk.utils
import cmk.utils.prediction as prediction

import cmk.gui.pages
import cmk.gui.sites as sites
from cmk.gui.i18n import _
from cmk.gui.globals import html
from cmk.gui.exceptions import MKGeneralException

graph_size = 2000, 700


@cmk.gui.pages.register("prediction_graph")
def page_graph():
    host = html.request.var("host")
    service = html.request.var("service")
    dsname = html.request.var("dsname")

    html.header(_("Prediction for %s - %s - %s") % (host, service, dsname))

    # Get current value from perf_data via Livestatus
    current_value = get_current_perfdata(host, service, dsname)

    pred_dir = prediction.predictions_dir(host, service, dsname, create=False)
    if pred_dir is None:
        raise MKGeneralException(
            _("There is currently no prediction information "
              "available for this service."))

    # Load all prediction information, sort by time of generation
    tg_name = html.request.var("timegroup")
    timegroup = None
    timegroups = []
    now = time.time()
    for f in os.listdir(pred_dir):
        if not f.endswith(".info"):
            continue

        tg_info = prediction.retrieve_data_for_prediction(pred_dir + "/" + f, timegroup)
        if tg_info is None:
            continue

        tg_info["name"] = f[:-5]
        timegroups.append(tg_info)
        if tg_info["name"] == tg_name or \
            (tg_name is None and now >= tg_info["range"][0] and now <= tg_info["range"][1]):
            timegroup = tg_info
            tg_name = tg_info["name"]

    timegroups.sort(key=lambda x: x["range"][0])

    choices = [(tg_info["name"], tg_info["name"].title()) for tg_info in timegroups]

    if not timegroup:
        if timegroups:
            timegroup = timegroups[0]
            tg_name = choices[0][0]
        else:
            raise MKGeneralException(_("Missing prediction information."))

    html.begin_form("prediction")
    html.write(_("Show prediction for "))
    html.dropdown("timegroup", choices, deflt=tg_name, onchange="document.prediction.submit();")
    html.hidden_fields()
    html.end_form()

    # Get prediction data
    path = pred_dir + "/" + timegroup["name"]
    tg_data = prediction.retrieve_data_for_prediction(path, tg_name)
    if tg_data is None:
        raise MKGeneralException(_("Missing prediction data."))

    swapped = swap_and_compute_levels(tg_data, timegroup['params'])
    vertical_range = compute_vertical_range(swapped)
    legend = [
        ("#000000", _("Reference")),
        ("#ffffff", _("OK area")),
        ("#ffff00", _("Warning area")),
        ("#ff0000", _("Critical area")),
    ]
    if current_value is not None:
        legend.append(("#0000ff", _("Current value: %.2f") % current_value))

    create_graph(timegroup["name"], graph_size, timegroup["range"], vertical_range, legend)

    if "levels_upper" in timegroup['params']:
        render_dual_area(swapped["upper_warn"], swapped["upper_crit"], "#fff000", 0.4)
        render_area_reverse(swapped["upper_crit"], "#ff0000", 0.1)

    if "levels_lower" in timegroup['params']:
        render_dual_area(swapped["lower_crit"], swapped["lower_warn"], "#fff000", 0.4)
        render_area(swapped["lower_crit"], "#ff0000", 0.1)

    vscala_low = vertical_range[0]
    vscala_high = vertical_range[1]
    vert_scala = compute_vertical_scala(vscala_low, vscala_high)
    time_scala = [[timegroup["range"][0] + i * 3600, "%02d:00" % i] for i in range(0, 25, 2)]
    render_coordinates(vert_scala, time_scala)

    if "levels_lower" in timegroup['params']:
        render_dual_area(swapped["average"], swapped["lower_warn"], "#ffffff", 0.5)
        render_curve(swapped["lower_warn"], "#e0e000", square=True)
        render_curve(swapped["lower_crit"], "#f0b0a0", square=True)

    if "levels_upper" in timegroup['params']:
        render_dual_area(swapped["upper_warn"], swapped["average"], "#ffffff", 0.5)
        render_curve(swapped["upper_warn"], "#e0e000", square=True)
        render_curve(swapped["upper_crit"], "#f0b0b0", square=True)
    render_curve(swapped["average"], "#000000")
    render_curve(swapped["average"], "#000000")  # repetition makes line bolder

    # Try to get current RRD data and render it also
    from_time, until_time = timegroup["range"]
    now = time.time()
    if now >= from_time and now <= until_time:
        timeseries = prediction.get_rrd_data(host, service, dsname, "MAX", from_time, until_time)
        rrd_data = timeseries.values

        render_curve(rrd_data, "#0000ff", 2)
        if current_value is not None:
            rel_time = (now - prediction.timezone_at(now)) % timegroup["slice"]
            render_point(timegroup["range"][0] + rel_time, current_value, "#0000ff")

    html.footer()


vranges = [
    ('n', 1024.0**-3),
    ('u', 1024.0**-2),
    ('m', 1024.0**-1),
    ('', 1024.0**0),
    ('K', 1024.0**1),
    ('M', 1024.0**2),
    ('G', 1024.0**3),
    ('T', 1024.0**4),
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
    steps = (max(0, high) - min(0, low)) / factor  # fixed: true-division
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
        vert_scala.append([v, "%.1f%s" % (v / factor, letter)])  # fixed: true-division
        v += step

    v = -factor
    while v >= min(0, low):
        vert_scala = [[v, "%.1f%s" % (v / factor, letter)]] + vert_scala  # fixed: true-division
        v -= step

    # Remove trailing ".0", if that is present for *all* entries
    for entry in vert_scala:
        if not entry[1].endswith(".0"):
            break
    else:
        vert_scala = [[e[0], e[1][:-2]] for e in vert_scala]

    return vert_scala


def get_current_perfdata(host, service, dsname):
    perf_data = sites.live().query_value(
        "GET services\nFilter: host_name = %s\nFilter: description = %s\n"
        "Columns: perf_data" % (livestatus.lqencode(host), livestatus.lqencode(service)))

    for part in perf_data.split():
        name, rest = part.split("=")
        if name == dsname:
            return float(rest.split(";")[0])


# Compute check levels from prediction data and check parameters
def swap_and_compute_levels(tg_data, tg_info):
    columns = tg_data["columns"]
    swapped = dict([(c, []) for c in columns])
    for step in tg_data["points"]:
        row = dict(zip(columns, step))
        for k, v in row.items():
            swapped[k].append(v)
        if row["average"] is not None and row["stdev"] is not None:
            _, (upper_0, upper_1, lower_0, lower_1) = prediction.estimate_levels(row, tg_info, 1.0)
            swapped.setdefault("upper_warn", []).append(upper_0 or 0)
            swapped.setdefault("upper_crit", []).append(upper_1 or 0)
            swapped.setdefault("lower_warn", []).append(lower_0 or 0)
            swapped.setdefault("lower_crit", []).append(lower_1 or 0)
        else:
            swapped.setdefault("upper_warn", []).append(0)
            swapped.setdefault("upper_crit", []).append(0)
            swapped.setdefault("lower_warn", []).append(0)
            swapped.setdefault("lower_crit", []).append(0)

    return swapped


def stack(apoints, bpoints, scale):
    return [a + scale * b for (a, b) in zip(apoints, bpoints)]


def compute_vertical_range(swapped):
    mmin, mmax = 0.0, 0.0
    for points in swapped.itervalues():
        mmax = max(mmax, max(points)) or 0.0  # convert None into 0.0
        mmin = min(mmin, min(points)) or 0.0
    return mmin, mmax


def create_graph(name, size, bounds, v_range, legend):
    html.write('<table class=prediction><tr><td>')
    html.write(
        '<canvas class=prediction id="content_%s" style="width: %dpx; height: %dpx;" width=%d height=%d></canvas>'
        % (name, int(size[0] / 2.0), int(size[1] / 2.0), size[0], size[1]))
    html.write('</td></tr><tr><td class=legend>')
    for color, title in legend:
        html.write('<div class=color style="background-color: %s"></div><div class=entry>%s</div>' %
                   (color, title))
    html.write('</div></td></tr></table>')
    html.javascript('cmk.prediction.create_graph("content_%s", %.4f, %.4f, %.4f, %.4f);' %
                    (name, bounds[0], bounds[1], v_range[0], v_range[1]))


def render_coordinates(v_scala, t_scala):
    html.javascript('cmk.prediction.render_coordinates(%s, %s);' %
                    (json.dumps(v_scala), json.dumps(t_scala)))


def render_curve(points, color, width=1, square=False):
    html.javascript('cmk.prediction.render_curve(%s, %s, %d, %d);' %
                    (json.dumps(points), json.dumps(color), width, square and 1 or 0))


def render_point(t, v, color):
    html.javascript('cmk.prediction.render_point(%s, %s, %s);' %
                    (json.dumps(t), json.dumps(v), json.dumps(color)))


def render_area(points, color, alpha=1.0):
    html.javascript('cmk.prediction.render_area(%s, %s, %f);' %
                    (json.dumps(points), json.dumps(color), alpha))


def render_area_reverse(points, color, alpha=1.0):
    html.javascript('cmk.prediction.render_area_reverse(%s, %s, %f);' %
                    (json.dumps(points), json.dumps(color), alpha))


def render_dual_area(lower_points, upper_points, color, alpha=1.0):
    html.javascript('cmk.prediction.render_dual_area(%s, %s, %s, %f);' %
                    (json.dumps(lower_points), json.dumps(upper_points), json.dumps(color), alpha))
