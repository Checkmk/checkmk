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
from cmk.gui.i18n import _
from cmk.gui.globals import html
from cmk.gui.plugins.sidebar import (
    sidebar_snapins,
    bulletlink,
    nagioscgilink,
    heading,
)


def render_nagios():
    html.open_ul()
    bulletlink("Home", "http://www.nagios.org")
    bulletlink("Documentation", "%snagios/docs/toc.html" % config.url_prefix())
    html.close_ul()
    for entry in [
            "General",
        ("tac.cgi", "Tactical Overview"),
        ("statusmap.cgi?host=all", "Map"),
            "Current Status",
        ("status.cgi?hostgroup=all&amp;style=hostdetail", "Hosts"),
        ("status.cgi?host=all", "Services"),
        ("status.cgi?hostgroup=all&amp;style=overview", "Host Groups"),
        ("status.cgi?hostgroup=all&amp;style=summary", "*Summary"),
        ("status.cgi?hostgroup=all&amp;style=grid", "*Grid"),
        ("status.cgi?servicegroup=all&amp;style=overview", "Service Groups"),
        ("status.cgi?servicegroup=all&amp;style=summary", "*Summary"),
        ("status.cgi?servicegroup=all&amp;style=grid", "*Grid"),
        ("status.cgi?host=all&amp;servicestatustypes=28", "Problems"),
        ("status.cgi?host=all&amp;type=detail&amp;hoststatustypes=3&amp;serviceprops=42&amp;servicestatustypes=28",
         "*Service (Unhandled)"),
        ("status.cgi?hostgroup=all&amp;style=hostdetail&amp;hoststatustypes=12&amp;hostprops=42",
         "*Hosts (Unhandled)"),
        ("outages.cgi", "Network Outages"),
            "Reports",
        ("avail.cgi", "Availability"),
        ("trends.cgi", "Trends"),
        ("history.cgi?host=all", "Alerts"),
        ("history.cgi?host=all", "*History"),
        ("summary.cgi", "*Summary"),
        ("histogram.cgi", "*Histogram"),
        ("notifications.cgi?contact=all", "Notifications"),
        ("showlog.cgi", "Event Log"),
            "System",
        ("extinfo.cgi?type=3", "Comments"),
        ("extinfo.cgi?type=6", "Downtime"),
        ("extinfo.cgi?type=0", "Process Info"),
        ("extinfo.cgi?type=4", "Performance Info"),
        ("extinfo.cgi?type=7", "Scheduling Queue"),
        ("config.cgi", "Configuration"),
    ]:
        if isinstance(entry, str):
            html.close_ul()
            heading(entry)
            html.open_ul()
        else:
            ref, text = entry
            if text[0] == "*":
                html.open_ul(class_="link")
                nagioscgilink(text[1:], ref)
                html.close_ul()
                heading(entry)
                html.open_ul()
            else:
                nagioscgilink(text, ref)


sidebar_snapins["nagios_legacy"] = {
    "title": _("Old Nagios GUI"),
    "description": _("The classical sidebar of Nagios 3.2.0 with links to "
                     "your local Nagios instance (no multi site support)"),
    "render": render_nagios,
    "allowed": [
        "user",
        "admin",
        "guest",
    ],
}
