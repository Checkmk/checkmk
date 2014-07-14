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
    "context_type": "global",
    "context"     : {},
    "title"       : _("Main Overview"),
    "topic"       : _("Overview"),
    "description" : _("This dashboard gives you a general overview on the state of your "
                      "monitored devices."),
    "dashlets" : [
        {
            "title"      : _("Host Statistics"),
            "type"       : 'hoststats',
            "position"   : (1, 1),
            "refresh"    : 60,
            "show_title" : True,
            "context"    : {},
        },
        {
            "title"      : _("Service Statistics"),
            "type"       : 'servicestats',
            "position"   : (31, 1),
            "refresh"    : 60,
            "show_title" : True,
            "context"    : {},
        },
        {
            "type"       : "view",
            "title"      : _("Host Problems (unhandled)"),
            "title_url"  : "view.py?view_name=hostproblems&is_host_acknowledged=0",
            "position"   : (-1, 1),
            "size"       : (GROW, 18),
            "show_title" : True,
            "context"    : {},

            'browser_reload': 30,
            'column_headers': 'pergroup',
            'datasource': 'hosts',
            'context_type': 'hosts',
            'group_painters': [],
            'hard_filters': ['host_scheduled_downtime_depth',
                             'summary_host',
                             'hoststate',
                             'host_acknowledged',
                             ],
            'hard_filtervars': [('is_host_scheduled_downtime_depth', '0'),
                                ('hst0', ''),
                                ('hst1', 'on'),
                                ('hst2', 'on'),
                                ('hstp', ''),
                                ('is_host_acknowledged', '0'),
                                ('is_summary_host', '0'),
                                ],
            'hidden': True,
            'hidebutton': True,
            'hide_filters': [],
            'layout': 'table',
            'mustsearch': False,
            'name': 'dashlet_2',
            'num_columns': 1,
            'owner': '',
            'painters': [
                         ('host_state', None),
                         ('host', 'host'),
                         ('host_icons', None),
                         ('host_state_age', None),
                         ('host_plugin_output', None),
                         ],
            'public': True,
            'show_filters': [],
            'sorters': [('hoststate', True)],
            'topic': None,
        },
        {
            "type"       : "view",
            "title"      : _("Service Problems (unhandled)"),
            "title_url"  : "view.py?view_name=svcproblems&is_service_acknowledged=0",
            "position"   : (1, 19),
            "size"       : (GROW, MAX),
            "show_title" : True,
            "context"    : {},

            'browser_reload': 30,
            'column_headers': 'pergroup',
            'datasource': 'services',
            'context_type': 'services',
            'group_painters': [],
            'hard_filters': ['service_acknowledged',
                             'svcstate',
                             'hoststate',
                             'summary_host',
                             'in_downtime'],
            'hard_filtervars': [('is_in_downtime', '0'),
                                ('is_service_acknowledged', '0'),
                                ('st0', ''),
                                ('st1', 'on'),
                                ('st2', 'on'),
                                ('st3', 'on'),
                                ('stp', ''),
                                ('hst0', 'on'),
                                ('hst1', ''),
                                ('hst2', ''),
                                ('hstp', 'on'),
                                ('is_summary_host', '0')],
            'hidden': True,
            'hide_filters': [],
            'layout': 'table',
            'mustsearch': False,
            'name': 'dashlet_3',
            'num_columns': 1,
            'owner': '',
            'painters': [('service_state', None),
                         ('host', 'host'),
                         ('service_description', 'service'),
                         ('service_icons', None),
                         ('svc_plugin_output', None),
                         ('svc_state_age', None),
                         ('svc_check_age', None),
                         ],
            'play_sounds': True,
            'public': True,
            'show_filters': [],
            'sorters': [('svcstate', True),
                        ('stateage', False),
                        ('svcdescr', False)],
        },
        {
            "type"       : "view",
            "title"      : _("Events of recent 4 hours"),
            "title_url"  : "view.py?view_name=events_dash",
            "position"   : (-1, -1),
            "size"       : (GROW, GROW),
            "show_title" : True,
            "context"    : {},

            'browser_reload': 90,
            'column_headers': 'pergroup',
            'datasource': 'log_events',
            'context_type': 'mkeventd_events',
            'group_painters': [],
            'hard_filters': ['logtime'],
            'hard_filtervars': [
                                ('logtime_from_range', '3600'),
                                ('logtime_from', '4'),
                                ],
            'hidden': True,
            'hide_filters': [],
            'layout': 'table',
            'linktitle': 'Events',
            'mustsearch': False,
            'name': 'dashlet_4',
            'num_columns': 1,
            'owner': 'admin',
            'painters': [('log_icon', None),
                         ('log_time', None),
                         ('host', 'hostsvcevents'),
                         ('service_description', 'svcevents'),
                         ('log_plugin_output', None)],


            'play_sounds': False,
            'public': True,
            'show_filters': [],
            'sorters': [],
        },
    ]
}

#Only work in OMD installations
if defaults.omd_site:
    builtin_dashboards["topology"] = {
        "context_type": "global",
        "context"     : {},
        "title"       : _("Network Topology"),
        "topic"       : _("Overview"),
        "description" : _("This dashboard uses the parent relationships of your hosts to display a "
                          "hierarchical map."),
        "dashlets" : [
            {
                "type"             : "url",
                "title"            : "Topology of Site " + defaults.omd_site,
                "url"              : defaults.url_prefix + 'nagvis/frontend/nagvis-js/index.php?' + \
                                     'mod=Map&header_template=on-demand-filter&header_menu=1&label_show=1' + \
                                     '&sources=automap&act=view&backend_id=' + defaults.omd_site + \
                                     '&render_mode=undirected&url_target=main',
                "reload_on_resize" : True,
                "position"         : (1, 0),
                "size"             : (GROW, GROW),
                "context"          : {},
            },
        ]
    }

builtin_dashboards["simple_problems"] = {
    "context_type": "global",
    "context"     : {},
    "title"       : _("Host &amp; Services Problems"),
    "topic"       : _("Overview"),
    "description" : _("A compact dashboard which lists your unhandled host and service problems."),
    "dashlets" : [
        {
            "type"       : "view",
            "title"      : _("Host Problems (unhandled)"),
            "title_url"  : "view.py?view_name=hostproblems&is_host_acknowledged=0",
            "show_title" : True,
            "position"   : (1, 1),
            "size"       : (GROW, 18),
            "context"    : {},

            'browser_reload': 30,
            'column_headers': 'pergroup',
            'datasource': 'hosts',
            'context_type': 'hosts',
            'group_painters': [],
            'hard_filters': ['host_scheduled_downtime_depth',
                             'summary_host',
                             'hoststate',
                             'host_acknowledged',
                             ],
            'hard_filtervars': [('is_host_scheduled_downtime_depth', '0'),
                                ('hst0', ''),
                                ('hst1', 'on'),
                                ('hst2', 'on'),
                                ('hstp', ''),
                                ('is_host_acknowledged', '0'),
                                ('is_summary_host', '0'),
                                ],
            'hidden': True,
            'hidebutton': True,
            'hide_filters': [],
            'layout': 'table',
            'mustsearch': False,
            'name': 'dashlet_0',
            'num_columns': 1,
            'owner': '',
            'painters': [
                         ('host_state', None),
                         ('host', 'host'),
                         ('host_icons', None),
                         ('host_state_age', None),
                         ('host_plugin_output', None),
                         ],
            'public': True,
            'show_filters': [],
            'sorters': [('hoststate', True)],
            'topic': None,
        },
        {
            "type"       : "view",
            "title"      : _("Service Problems (unhandled)"),
            "title_url"  : "view.py?view_name=svcproblems&is_service_acknowledged=0",
            "show_title" : True,
            "position"   : (1, 19),
            "size"       : (GROW, MAX),
            "context"    : {},

            'browser_reload': 30,
            'column_headers': 'pergroup',
            'datasource': 'services',
            'context_type': 'services',
            'group_painters': [],
            'hard_filters': ['service_acknowledged',
                             'svcstate',
                             'hoststate',
                             'summary_host',
                             'in_downtime'],
            'hard_filtervars': [('is_in_downtime', '0'),
                                ('is_service_acknowledged', '0'),
                                ('st0', ''),
                                ('st1', 'on'),
                                ('st2', 'on'),
                                ('st3', 'on'),
                                ('stp', ''),
                                ('hst0', 'on'),
                                ('hst1', ''),
                                ('hst2', ''),
                                ('hstp', 'on'),
                                ('is_summary_host', '0')],
            'hidden': True,
            'hide_filters': [],
            'layout': 'table',
            'mustsearch': False,
            'name': 'dashlet_1',
            'num_columns': 1,
            'owner': '',
            'painters': [('service_state', None),
                         ('host', 'host'),
                         ('service_description', 'service'),
                         ('service_icons', None),
                         ('svc_plugin_output', None),
                         ('svc_state_age', None),
                         ('svc_check_age', None),
                         ],
            'play_sounds': True,
            'public': True,
            'show_filters': [],
            'sorters': [('svcstate', True),
                        ('stateage', False),
                        ('svcdescr', False)],
        },
    ]
}

