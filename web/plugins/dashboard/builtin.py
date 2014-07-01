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

builtin_dashboards["main"] = {
    "title"       : _("Main Overview"),
    "topic"       : _("Overview"),
    "description" : _("This dashboard gives you a general overview on the state of your "
                      "monitored devices."),
    "dashlets" : [
        {
            "title"      : _("Host Statistics"),
            "type"       : 'hoststats',
            "position"   : (1, 1),
            "shadow"     : True,
            "refresh"    : 60,
            "parameters" : {},
        },
        {
            "title"      : _("Service Statistics"),
            "url"        : "dashlet_servicestats.py",
            "position"   : (31, 1),
            "shadow"     : True,
            "refresh"    : 60,
            "parameters" : {},
        },
        {
            "type"       : "view",
            "title"      : _("Host Problems (unhandled)"),
            "title_url"  : "view.py?view_name=hostproblems&is_host_acknowledged=0",
            "position"   : (-1, 1),
            "size"       : (GROW, 18),
            "parameters" : {"view_name": "hostproblems_dash"},
        },
        {
            "type"       : "view",
            "title"      : _("Service Problems (unhandled)"),
            "title_url"  : "view.py?view_name=svcproblems&is_service_acknowledged=0",
            "position"   : (1, 19),
            "size"       : (GROW, MAX),
            "parameters" : {"view_name": "svcproblems_dash"},
        },
        {
            "type"       : "view",
            "title"      : _("Events of recent 4 hours"),
            "title_url"  : "view.py?view_name=events_dash",
            "position"   : (-1, -1),
            "size"       : (GROW, GROW),
            "parameters" : {"view_name": "events_dash"},
        },
    ]
}

#Only work in OMD installations
if defaults.omd_site:
    builtin_dashboards["topology"] = {
        "title"       : _("Network Topology"),
        "topic"       : _("Overview"),
        "description" : _("This dashboard uses the parent relationships of your hosts to display a "
                          "hierarchical map."),
        "dashlets" : [
            {
                "type"             : "url",
                "title"            : "Topology of Site " + defaults.omd_site,
                "iframe"           : defaults.url_prefix + 'nagvis/frontend/nagvis-js/index.php?' + \
                                     'mod=Map&header_template=on-demand-filter&header_menu=1&label_show=1' + \
                                     '&sources=automap&act=view&backend_id=' + defaults.omd_site + \
                                     '&render_mode=undirected&url_target=main',
                "reload_on_resize" : True,
                "position"         : (1, 0),
                "size"             : (GROW, GROW),
                "parameters"       : {},
            },
        ]
    }

builtin_dashboards["simple_problems"] = {
    "title"       : _("Host &amp; Services Problems"),
    "topic"       : _("Overview"),
    "description" : _("A compact dashboard which lists your unhandled host and service problems."),
    "dashlets" : [
        {
            "title"      : _("Host Problems (unhandled)"),
            "title_url"  : "view.py?view_name=hostproblems&is_host_acknowledged=0",
            "view"       : "hostproblems_dash",
            "position"   : (1, 1),
            "size"       : (GROW, 18),
            "parameters" : {},
        },
        {
            "title"      : _("Service Problems (unhandled)"),
            "title_url"  : "view.py?view_name=svcproblems&is_service_acknowledged=0",
            "view"       : "svcproblems_dash",
            "position"   : (1, 19),
            "size"       : (GROW, MAX),
            "parameters" : {},
        },
    ]
}

