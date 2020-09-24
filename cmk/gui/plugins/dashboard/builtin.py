#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _

from cmk.gui.plugins.dashboard import (
    builtin_dashboards,
    GROW,
    MAX,
)

builtin_dashboards["main"] = {
    "single_infos": [],
    "context": {},
    "mtime": 0,
    "show_title": True,
    "title": _("Main Overview"),
    "topic": "overview",
    "sort_index": 10,
    "icon": "dashboard",
    "description": _("This dashboard gives you a general overview on the state of your "
                     "monitored devices."),
    "dashlets": [
        {
            "title": _("Host Statistics"),
            "type": 'hoststats',
            "position": (1, 1),
            "refresh": 60,
            "show_title": True,
            'context': {
                'wato_folder': {
                    'wato_folder': '',
                }
            },
            'single_infos': [],
        },
        {
            "title": _("Service Statistics"),
            "type": 'servicestats',
            "position": (31, 1),
            "refresh": 60,
            "show_title": True,
            'context': {
                'wato_folder': {
                    'wato_folder': '',
                }
            },
            'single_infos': [],
        },
        {
            "type": "view",
            "title": _("Host Problems (unhandled)"),
            "title_url": "view.py?view_name=hostproblems&is_host_acknowledged=0",
            "position": (-1, 1),
            "size": (GROW, 18),
            "show_title": True,
            'browser_reload': 30,
            'column_headers': 'pergroup',
            'datasource': 'hosts',
            'single_infos': [],
            'group_painters': [],
            'context': {
                'hoststate': {
                    'hst0': '',
                    'hst1': 'on',
                    'hst2': 'on',
                    'hstp': '',
                },
                'host_acknowledged': {
                    'is_host_acknowledged': '0'
                },
                'host_scheduled_downtime_depth': {
                    'is_host_scheduled_downtime_depth': '0'
                },
            },
            'hidden': True,
            'hidebutton': True,
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
            'sorters': [('hoststate', True)],
            'topic': None,
        },
        {
            "type": "view",
            "title": _("Service Problems (unhandled)"),
            "title_url": "view.py?view_name=svcproblems&is_service_acknowledged=0",
            "position": (1, 19),
            "size": (GROW, MAX),
            "show_title": True,
            'browser_reload': 30,
            'column_headers': 'pergroup',
            'datasource': 'services',
            'single_infos': [],
            'group_painters': [],
            'context': {
                'service_acknowledged': {
                    'is_service_acknowledged': '0'
                },
                'in_downtime': {
                    'is_in_downtime': '0'
                },
                'hoststate': {
                    'hst0': 'on',
                    'hst1': '',
                    'hst2': '',
                    'hstp': 'on'
                },
                'svcstate': {
                    'st0': '',
                    'st1': 'on',
                    'st2': 'on',
                    'st3': 'on',
                    'stp': '',
                }
            },
            'hidden': True,
            'layout': 'table',
            'mustsearch': False,
            'name': 'dashlet_3',
            'num_columns': 1,
            'owner': '',
            'painters': [
                ('service_state', None),
                ('host', 'host'),
                ('service_description', 'service'),
                ('service_icons', None),
                ('svc_plugin_output', None),
                ('svc_state_age', None),
                ('svc_check_age', None),
            ],
            'play_sounds': True,
            'public': True,
            'sorters': [('svcstate', True), ('stateage', False), ('svcdescr', False)],
        },
        {
            "type": "view",
            "title": _("Events of recent 4 hours"),
            "title_url": "view.py?view_name=events_dash",
            "position": (-1, -1),
            "size": (GROW, GROW),
            "show_title": True,
            'browser_reload': 90,
            'column_headers': 'pergroup',
            'datasource': 'log_events',
            'single_infos': [],
            'group_painters': [],
            'context': {
                'logtime': {
                    'logtime_from_range': '3600',
                    'logtime_from': '4',
                },
            },
            'hidden': True,
            'layout': 'table',
            'linktitle': 'Events',
            'mustsearch': False,
            'name': 'dashlet_4',
            'num_columns': 1,
            'owner': 'admin',
            'painters': [('log_icon', None), ('log_time', None), ('host', 'hostsvcevents'),
                         ('service_description', 'svcevents'), ('log_plugin_output', None)],
            'play_sounds': False,
            'public': True,
            'sorters': [('log_time', True)],
        },
    ]
}

builtin_dashboards["topology"] = {
    "single_infos": [],
    "context": {},
    "mtime": 0,
    "show_title": False,
    "title": _("Network Topology"),
    "topic": "overview",
    "icon": "network_topology",
    "sort_index": 50,
    "description": _("This dashboard uses the parent relationships of your hosts to display a "
                     "hierarchical map."),
    "dashlets": [{
        'add_context_to_title': True,
        'link_from': {},
        'background': True,
        'context': {},
        'position': (1, 1),
        'show_in_iframe': True,
        'show_title': False,
        'single_infos': [],
        'size': (GROW, GROW),
        'type': 'url',
        'url': 'parent_child_topology.py'
    }],
}

builtin_dashboards["simple_problems"] = {
    "single_infos": [],
    "context": {},
    "mtime": 0,
    "show_title": True,
    "title": _("Host & service problems"),
    "topic": "problems",
    "icon": "host_svc_problems",
    "sort_index": 10,
    "description": _("A compact dashboard which lists your unhandled host and service problems."),
    "dashlets": [
        {
            "type": "view",
            "title": _("Host Problems (unhandled)"),
            "title_url": "view.py?view_name=hostproblems&is_host_acknowledged=0",
            "show_title": True,
            "position": (1, 1),
            "size": (GROW, 18),
            'browser_reload': 30,
            'column_headers': 'pergroup',
            'datasource': 'hosts',
            'single_infos': [],
            'group_painters': [],
            'context': {
                'host_acknowledged': {
                    'is_host_acknowledged': '0'
                },
                'host_scheduled_downtime_depth': {
                    'is_host_scheduled_downtime_depth': '0'
                },
                'hoststate': {
                    'hst0': '',
                    'hst1': 'on',
                    'hst2': 'on',
                    'hstp': ''
                },
            },
            'hidden': True,
            'hidebutton': True,
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
            'sorters': [('hoststate', True)],
            'topic': None,
        },
        {
            "type": "view",
            "title": _("Service Problems (unhandled)"),
            "title_url": "view.py?view_name=svcproblems&is_service_acknowledged=0",
            "show_title": True,
            "position": (1, 19),
            "size": (GROW, MAX),
            'browser_reload': 30,
            'column_headers': 'pergroup',
            'datasource': 'services',
            'single_infos': [],
            'group_painters': [],
            'context': {
                'service_acknowledged': {
                    'is_service_acknowledged': '0'
                },
                'in_downtime': {
                    'is_in_downtime': '0'
                },
                'hoststate': {
                    'hst0': 'on',
                    'hst1': '',
                    'hst2': '',
                    'hstp': 'on'
                },
                'svcstate': {
                    'st0': '',
                    'st1': 'on',
                    'st2': 'on',
                    'st3': 'on',
                    'stp': '',
                }
            },
            'hidden': True,
            'layout': 'table',
            'mustsearch': False,
            'name': 'dashlet_1',
            'num_columns': 1,
            'owner': '',
            'painters': [
                ('service_state', None),
                ('host', 'host'),
                ('service_description', 'service'),
                ('service_icons', None),
                ('svc_plugin_output', None),
                ('svc_state_age', None),
                ('svc_check_age', None),
            ],
            'play_sounds': True,
            'public': True,
            'sorters': [('svcstate', True), ('stateage', False), ('svcdescr', False)],
        },
    ]
}

builtin_dashboards["cmk_overview"] = {
    "topic": "analyze",
    "sort_index": 70,
    'name': 'cmk_overview',
    'hidebutton': False,
    'title': u'Checkmk overview',
    'description': u'Displays an overview of all Checkmk servers and instances\n',
    'add_context_to_title': False,
    'link_from': {},
    'context': {},
    'hidden': False,
    "mtime": 0,
    'linktitle': u'Checkmk',
    'show_title': True,
    'dashlets': [{
        'background': True,
        'type': 'linked_view',
        'name': 'cmk_servers',
        'add_context_to_title': True,
        'link_from': {},
        'context': {},
        'position': (1, 1),
        'show_title': True,
        'single_infos': [],
        'size': (0, 0)
    }, {
        'name': 'cmk_sites',
        'title': u'Site overview',
        'show_title': True,
        'background': True,
        'add_context_to_title': True,
        'link_from': {},
        'context': {},
        'position': (1, 47),
        'type': 'linked_view',
        'single_infos': [],
        'size': (0, 0)
    }],
    'single_infos': [],
    'icon': 'checkmk'
}

builtin_dashboards['cmk_host'] = {
    'add_context_to_title': True,
    'description': u'Display information relevant for the Checkmk performance\n',
    'link_from': {
        'single_infos': ['host'],
        'host_labels': {
            'cmk/check_mk_server': 'yes'
        }
    },
    'title': u'Checkmk server',
    'hidebutton': False,
    'dashlets': [{
        'show_title': True,
        'link_from': {},
        'background': True,
        'add_context_to_title': True,
        'context': {},
        'position': (-1, 29),
        'size': (0, 0),
        'type': 'linked_view',
        'single_infos': [],
        'name': 'cmk_sites_of_host'
    }, {
        'context': {
            'service': u'CPU load'
        },
        'link_from': {},
        'type': 'single_metric',
        'time_range': 'current',
        'metric': u'load5',
        'add_context_to_title': True,
        'render_options': {
            'show_site': 'false',
            'font_size': 'dynamic',
            'show_state_color': 'background',
            'show_metric': 'tooltip',
            'show_unit': 'true',
            'link_to_svc_detail': 'true',
            'show_host': 'false',
            'show_service': ('above', 12.0)
        },
        'background': True,
        'position': (1, 1),
        'show_title': False,
        'single_infos': ['service', 'host'],
        'size': (26, 14)
    }, {
        'add_context_to_title': True,
        'context': {
            'service': u'Disk IO SUMMARY'
        },
        'background': True,
        'link_from': {},
        'timerange': '1',
        'graph_render_options': {
            'font_size': 8.0,
            'show_graph_time': True,
            'show_time_axis': True,
            'foreground_color': 'default',
            'title_format': 'plain',
            'canvas_color': 'default',
            'show_legend': False,
            'show_title': True,
            'show_margin': True,
            'vertical_axis_width': 'fixed',
            'show_controls': False,
            'show_pin': True,
            'background_color': 'default',
            'show_vertical_axis': True
        },
        'source': 8,
        'show_title': False,
        'position': (-36, 15),
        'type': 'pnpgraph',
        'single_infos': ['service', 'host'],
        'size': (0, 14)
    }, {
        'add_context_to_title': True,
        'context': {
            'service': u'Kernel Performance'
        },
        'background': True,
        'link_from': {},
        'timerange': '1',
        'graph_render_options': {
            'font_size': 8.0,
            'show_graph_time': True,
            'show_time_axis': True,
            'foreground_color': 'default',
            'title_format': 'plain',
            'canvas_color': 'default',
            'show_legend': False,
            'show_title': True,
            'show_margin': True,
            'vertical_axis_width': 'fixed',
            'show_controls': False,
            'show_pin': True,
            'background_color': 'default',
            'show_vertical_axis': True
        },
        'source': 2,
        'show_title': False,
        'position': (27, 15),
        'type': 'pnpgraph',
        'single_infos': ['service', 'host'],
        'size': (0, 14)
    }, {
        'add_context_to_title': True,
        'context': {
            'service': u'Memory'
        },
        'link_from': {},
        'type': 'pnpgraph',
        'timerange': '1',
        'graph_render_options': {
            'font_size': 8.0,
            'show_graph_time': True,
            'show_time_axis': True,
            'foreground_color': 'default',
            'title_format': 'plain',
            'vertical_axis_width': 'fixed',
            'show_legend': False,
            'show_title': True,
            'show_margin': True,
            'canvas_color': 'default',
            'show_controls': False,
            'show_pin': True,
            'background_color': 'default',
            'show_vertical_axis': True
        },
        'source': 1,
        'background': True,
        'position': (27, 1),
        'show_title': False,
        'single_infos': ['service', 'host'],
        'size': (0, 14)
    }, {
        'add_context_to_title': True,
        'context': {
            'host': u'heute',
            'service': u'Disk IO SUMMARY'
        },
        'background': True,
        'link_from': {},
        'timerange': '1',
        'graph_render_options': {
            'font_size': 8.0,
            'show_graph_time': True,
            'show_time_axis': True,
            'foreground_color': 'default',
            'title_format': 'plain',
            'vertical_axis_width': 'fixed',
            'show_legend': False,
            'show_title': True,
            'show_margin': True,
            'canvas_color': 'default',
            'show_controls': False,
            'show_pin': True,
            'background_color': 'default',
            'show_vertical_axis': True
        },
        'source': 2,
        'show_title': False,
        'position': (-36, 1),
        'type': 'pnpgraph',
        'single_infos': ['service', 'host'],
        'size': (0, 14)
    }, {
        'context': {
            'service': u'Filesystem /'
        },
        'link_from': {},
        'type': 'single_metric',
        'time_range': 'current',
        'metric': u'fs_used',
        'add_context_to_title': True,
        'render_options': {
            'show_site': 'false',
            'font_size': 'dynamic',
            'show_state_color': 'background',
            'show_metric': 'tooltip',
            'show_service': ('above', 12.0),
            'link_to_svc_detail': 'true',
            'show_host': 'false',
            'show_unit': 'true'
        },
        'background': True,
        'position': (1, 15),
        'show_title': False,
        'single_infos': ['host', 'service'],
        'size': (26, 14)
    }, {
        'force_checkboxes': False,
        'background': True,
        'play_sounds': False,
        'num_columns': 1,
        'size': (35, 28),
        'group_painters': [],
        'layout': 'table',
        'title': u'Network',
        'painters': [
            ('service_state', None, None),
            ('service_description', None, None),
            ('perfometer', None, None),
        ],
        'column_headers': 'off',
        'type': 'view',
        'columns': {
            'columns': [
                ('service_state', None, None),
                ('service_description', None, None),
                ('perfometer', None, None),
            ]
        },
        'link_from': {},
        'visibility': {},
        'add_context_to_title': True,
        'user_sortable': False,
        'show_title': True,
        'grouping': {
            'grouping': []
        },
        'sorting': {
            'sorters': [('svcdescr', False)]
        },
        'name': 'dashlet_7',
        'mobile': False,
        'browser_reload': 0,
        'sorters': [('svcdescr', False)],
        'datasource': 'services',
        'context': {
            'serviceregex': {
                'service_regex': 'Interface',
                'neg_service_regex': ''
            }
        },
        'position': (-1, 1),
        'view': {
            'layout': 'table',
            'browser_reload': 0,
            'datasource': 'services',
            'num_columns': 1,
            'column_headers': 'pergroup',
            'options': []
        },
        'single_infos': ['host'],
        'mustsearch': False
    }],
    'name': 'cmk_host',
    'topic': u'Applications',
    'context': {},
    'mtime': 0,
    'owner': '',
    'hidden': True,
    'linktitle': u'Checkmk',
    'show_title': True,
    'public': False,
    'single_infos': ['host'],
    'icon': 'checkmk'
}
