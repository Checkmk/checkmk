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

import cmk.gui.config as config
import cmk.gui.sites as sites
from cmk.gui.i18n import _
from cmk.gui.globals import html

from cmk.gui.plugins.sidebar import (
    sidebar_snapins,
    snapin_width,
    snapin_site_choice,
)


def render_performance():
    only_sites = snapin_site_choice("performance", config.site_choices())

    def write_line(left, right):
        html.open_tr()
        html.td(left, class_="left")
        html.td(html.render_strong(right), class_="right")
        html.close_tr()

    html.open_table(class_=["content_center", "performance"])

    try:
        sites.live().set_only_sites(only_sites)
        data = sites.live().query("GET status\nColumns: service_checks_rate host_checks_rate "
                                  "external_commands_rate connections_rate forks_rate "
                                  "log_messages_rate cached_log_messages\n")
    finally:
        sites.live().set_only_sites(None)

    for what, col, format_str in \
        [("Service checks",         0, "%.2f/s"),
         ("Host checks",            1, "%.2f/s"),
         ("External commands",      2, "%.2f/s"),
         ("Livestatus-conn.",       3, "%.2f/s"),
         ("Process creations",      4, "%.2f/s"),
         ("New log messages",       5, "%.2f/s"),
         ("Cached log messages",    6, "%d")]:
        write_line(what + ":", format_str % sum(row[col] for row in data))

    if only_sites is None and len(config.allsites()) == 1:
        try:
            data = sites.live().query("GET status\nColumns: external_command_buffer_slots "
                                      "external_command_buffer_max\n")
        finally:
            sites.live().set_only_sites(None)
        size = sum([row[0] for row in data])
        maxx = sum([row[1] for row in data])
        write_line(_('Com. buf. max/total'), "%d / %d" % (maxx, size))

    html.close_table()


sidebar_snapins["performance"] = {
    "title": _("Server Performance"),
    "description": _("Live monitor of the overall performance of all monitoring servers"),
    "refresh": True,
    "render": render_performance,
    "allowed": ["admin",],
    "styles": """
#snapin_performance select {
    margin-bottom: 2px;
    width: 100%%;
}
table.performance {
    width: %dpx;
    border-radius: 2px;
    background-color: rgba(0, 0, 0, 0.1);
    border-style: solid;
    border-color: rgba(0, 0, 0, 0.3) rgba(255, 255, 255, 0.3) rgba(255, 255, 255, 0.3) rgba(0, 0, 0, 0.3);
    border-width: 1.5px;
}
table.performance td {
    padding: 0px 2px;
    font-size: 8pt;
}
table.performance td.right {
    text-align: right;
    padding: 0px;
    padding-right: 1px;
    white-space: nowrap;
}

""" % (snapin_width - 2)
}
