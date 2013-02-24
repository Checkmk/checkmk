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
            tg = eval(file(dir + "/" + f).read())
            tg["name"] = f[:-5]
            timegroups.append(tg)

    timegroups.sort(cmp = lambda a,b: cmp(a["time"], b["time"]))
    for tg in timegroups:
        render_timegroup(dir, tg)

    html.footer()

def render_timegroup(dir, tg):
    data = eval(file(dir + "/" + tg["name"]).read())
    html.write('<div class=prediction>')
    html.write('<h3>%s</h3>' % (_("Prediction for %s") % tg["name"]))
    html.write('<canvas class=prediction id="content_%s" width=800 height=300></canvas>' % tg["name"])
    html.write('</div>')
    html.javascript("var data_%s = %r;" % (tg["name"], data))
    html.javascript('render_prediction("content_%s", data_%s);' % (
            tg["name"],tg["name"]))

