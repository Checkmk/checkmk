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

import mkeventd

try:
    mkeventd_enabled = config.mkeventd_enabled
except:
    mkeventd_enabled = False

def render_mkeventd_performance():
    def write_line(left, right):
        html.write("<tr><td class=left>%s:</td>"
                   "<td class=right><strong>%s</strong></td></tr>" % (left, right))

    html.write("<table class=\"content_center mkeventd_performance\">\n")

    raw_data = mkeventd.query("GET status")
    data = dict(zip(raw_data[0], raw_data[1]))
    columns = [
          (_("Received messages"),   "message",   "%.2f/s"),
          (_("Rule hits"),           "rule_hit",  "%.2f/s"),
          (_("Rule tries"),          "rule_trie", "%.2f/s"),
          (_("Created events"),      "event",     "%.2f/s"),
          (_("Client connects"),     "connect",   "%.2f/s"),
    ]
    for what, col, format in columns:
        write_line(what, format % data["status_average_%s_rate" % col])

    # Hit rate
    try:
        write_line(_("Rule hit ratio"), "%.2f %%" % (
           data["status_average_rule_hit_rate"] / 
           data["status_average_rule_trie_rate"] * 100))
    except: # division by zero
        write_line(_("Rule hit ratio"), _("-.-- %"))
        pass

    # Time columns
    time_columns = [
        (_("Processing time per message"), "processing"),
        (_("Time per client request"), "request"),
        (_("Replication synchronization"), "sync"),
    ]
    for title, name in time_columns:
        value = data.get("status_average_%s_time" % name)
        if value:
            write_line(title, "%.2f ms" % (value * 1000))
        else:
            write_line(title, _("-.-- ms"))
    html.write("</table>\n")

if mkeventd_enabled:
    sidebar_snapins["mkeventd_performance"] = {
        "title" : _("Event Console Performance"),
        "description" : _("Monitor the performance of the Event Console"),
        "refresh" : 15,
        "render" : render_mkeventd_performance,
        "allowed" : [ "admin", ],
        "styles" : """
    table.mkeventd_performance {
        width: %dpx;
        -moz-border-radius: 5px;
        background-color: #589;
        /* background-color: #6da1b8;*/
        border-style: solid;
        border-color: #444 #bbb #eee #666;
        /* The border needs to be substracted from the width */
        border-width: 1px;
    }
    table.mkeventd_performance td {
        padding: 0px 2px;
        font-size: 8pt;
    }
    table.mkeventd_performance td.right {
        text-align: right;
        padding: 0px;
        padding-right: 1px;
        white-space: nowrap;
    }

    """ % (snapin_width - 2)
    }
