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
from lib import *

graph_size = 2000, 700

def page_graph():
    host = html.var("host")
    service = html.var("service")
    dsname = html.var("dsname")
    html.header(_("Prediction for %s - %s - %s") % 
            (host, service, dsname), 
            javascripts=["prediction"],
            stylesheets=["pages", "prediction"])

    dir = "%s/prediction/%s/%s/%s" % (
            defaults.var_dir, host, pnp_cleanup(service), pnp_cleanup(dsname))

    # Load all prediction information, sort by time of generation
    timegroups = []
    for f in os.listdir(dir):
        if f.endswith(".info"):
            tg_info = eval(file(dir + "/" + f).read())
            tg_info["name"] = f[:-5]
            timegroups.append(tg_info)

    timegroups.sort(cmp = lambda a,b: cmp(a["range"], b["range"]))
    for tg_info in timegroups:
        title = _("Prediction for %s") % tg_info["name"]
        # time_range aus info-Datei holen
        # v_range ermitteln
        tg_data = eval(file(dir + "/" + tg_info["name"]).read())
        swapped = swap_and_compute_levels(tg_data, tg_info)
        vertical_range = compute_vertical_range(swapped)
        legend = [
           ( "#ff0000", _("Critical area") ),
           ( "#ffff00", _("Warning area") ),
           ( "#ffffff", _("OK area") ),
           ( "#000000", _("Reference") ),
        ]
        create_graph(tg_info["name"], title, graph_size, tg_info["range"], vertical_range, legend)

        if "levels_upper" in tg_info:
            render_dual_area(swapped["upper_warn"], swapped["upper_crit"], "#fff000", 0.4)
            render_area_reverse(swapped["upper_crit"], "#ff0000", 0.1)

        if "levels_lower" in tg_info:
            render_dual_area(swapped["lower_crit"], swapped["lower_warn"], "#fff000", 0.4)
            render_area(swapped["lower_crit"], "#ff0000", 0.1)

        vert_scala = [ [x, "%.1f" % x] for x in range(int(vertical_range[0]), int(vertical_range[1] + 1)) ]
        time_scala = [ [tg_info["range"][0] + i*3600, "%02d:00" % i] for i in range(0, 25, 2) ] 
        render_coordinates(vert_scala, time_scala);

        if "levels_lower" in tg_info:
            render_dual_area(swapped["average"], swapped["lower_warn"], "#ffffff", 0.5)
            render_curve(swapped["lower_warn"], "#e0e000")
            render_curve(swapped["lower_crit"], "#j0b0a0")

        if "levels_upper" in tg_info:
            render_dual_area(swapped["upper_warn"], swapped["average"], "#ffffff", 0.5)
            render_curve(swapped["upper_warn"], "#e0e000")
            render_curve(swapped["upper_crit"], "#f0b0b0")
        render_curve(swapped["average"], "#000000")
        render_curve(swapped["average"], "#000000")
        # render_curve(stack(swapped["average"], swapped["stdev"], -1),  "#008040")

    html.footer()

# Compute check levels from prediction data and check parameters
def swap_and_compute_levels(tg_data, tg_info):
    columns = tg_data["columns"]
    swapped = dict([ (c, []) for c in columns])
    for step in tg_data["points"]:
        row = dict(zip(columns, step))
        for k, v in row.items():
            swapped[k].append(v)
        upper, lower = compute_levels(tg_info, row["average"], row["stdev"])
        if upper[0] != None:
            swapped.setdefault("upper_warn", []).append(upper[0])
            swapped.setdefault("upper_crit", []).append(upper[1])
        if lower[0] != None:
            swapped.setdefault("lower_warn", []).append(lower[0])
            swapped.setdefault("lower_crit", []).append(lower[1])
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
        mmax = max(mmax, max(points))
        mmin = min(mmin, min(points))
    return mmin, mmax

def create_graph(name, title, size, range, v_range, legend):
    html.write('<h3 class=prediction>%s</h3>' % title)
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


def render_curve(points, color):
    html.javascript('render_curve(%r, %r);' % (points, color))

def render_area(points, color, alpha=1.0):
    html.javascript('render_area(%r, %r, %f);' % (points, color, alpha))

def render_area_reverse(points, color, alpha=1.0):
    html.javascript('render_area_reverse(%r, %r, %f);' % (points, color, alpha))

def render_dual_area(lower_points, upper_points, color, alpha=1.0):
    html.javascript('render_dual_area(%r, %r, %r, %f);' % (lower_points, upper_points, color, alpha))
