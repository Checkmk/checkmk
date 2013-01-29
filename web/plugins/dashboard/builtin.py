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
    "title" : _("Main Overview"),
    "dashlets" : [
#         {
#             "url"        : "dashlet_mk_logo.py",
#             "position"   : (1, 1),
#             "size"       : (4, 5),
#             "shadow"     : False,
#             "background" : False,
#         },
        {
            "title"      : _("Host Statistics"),
            "url"        : "dashlet_hoststats.py",
            "position"   : (1, 1),
            "size"       : (30, 18),
            "shadow"     : True,
            "background" : True,
            "refresh"    : 60,
        },
        {
            "title"      : _("Service Statistics"),
            "url"        : "dashlet_servicestats.py",
            "position"   : (31, 1),
            "size"       : (30, 18),
            "shadow"     : True,
            "background" : True,
            "refresh"    : 60,
        },
        {
            "title"      : _("Host Problems (unhandled)"),
            "title_url"  : "view.py?view_name=hostproblems&is_host_acknowledged=0",
            "view"       : "hostproblems_dash", # "view.py?view_name=hostproblems_dash&display_options=SIXHR&_body_class=dashlet",
            "position"   : (-1, 1),
            "size"       : (GROW, 18),
        },
        {
            "title"      : _("Service Problems (unhandled)"),
            "title_url"  : "view.py?view_name=svcproblems&is_service_acknowledged=0",
            "view"       : "svcproblems_dash", # "view.py?view_name=svcproblems_dash&display_options=SIXHR&_body_class=dashlet",
            "position"   : (1, 19),
            "size"       : (GROW, MAX),
        },
        {
            "title"      : _("Events of recent 4 hours"),
            "title_url"  : "view.py?view_name=events_dash",
            "view"       : "events_dash", # "view.py?view_name=events_dash&display_options=SIXHR&_body_class=dashlet",
            "position"   : (-1, -1),
            "size"       : (GROW, GROW),
        },
        # {
        #     "title"    : "CPU load of Nagios",
        #     # "url"      : "http://localhost/dk/pnp4nagios/index.php/image?host=DerNagiosSelbst&srv=fs__var&view=0",
        #     "url"      : "http://localhost/dk/pnp4nagios/index.php/popup?host=localhost&srv=CPU_load&view=0&source=2",
        #     "position" : (1, -1),
        #     "size"     : (11, 5),
        # },
        # {
        #     "title"    : "CPU utilization of Nagios",
        #     # "url"      : "http://localhost/dk/pnp4nagios/index.php/image?host=DerNagiosSelbst&srv=fs__var&view=0",
        #     "url"      : "http://localhost/dk/pnp4nagios/index.php/popup?host=localhost&srv=CPU_utilization&view=0&source=2",
        #     "position" : (12, -1),
        #     "size"     : (11, 5),
        # },
        # {
    ]
}
