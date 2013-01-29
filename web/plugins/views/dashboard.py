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

multisite_builtin_views.update({

# A similar view, used in the dashboard
 'hostproblems_dash': {
                  'browser_reload': 30,
                  'column_headers': 'pergroup',
                  'datasource': 'hosts',
                  'description': 'A complete list of all host problems, optimized for usage in the dashboard',
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
                  'hidden': False,
                  'hidebutton': True,
                  'hide_filters': [],
                  'layout': 'table',
                  'mustsearch': False,
                  'name': 'hostproblems',
                  'num_columns': 1,
                  'owner': '',
                  'painters': [
                               ('host_state', None),
                               ('host', 'host'),
                               ('host_icons', None),
                               ('host_state_age', None),
                               ('host_plugin_output', None),
                               # ('host_check_age', None),       # save space
                               # ('num_services_ok', 'host_ok'), # save space
                               #('num_services_warn', 'host_warn'),
                               #('num_services_crit', 'host_crit'),
                               #('num_services_unknown', 'host_unknown'),
                               #('num_services_pending', 'host_pending'),
                               ],
                  'public': True,
                  'show_filters': [],
                  'sorters': [('hoststate', True)],
                  'title': 'Host problems',
                  'topic': None,
                  },

 # Similar view, but for the dashboard
 'svcproblems_dash': {
                 'browser_reload': 30,
                 'column_headers': 'pergroup',
                 'datasource': 'services',
                 'description': 'All non-downtime, non-acknownledged services, used for the dashbaord',
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
                 'hidden': False,
                 'hide_filters': [],
                 'layout': 'table',
                 'mustsearch': False,
                 'name': 'svcproblems',
                 'num_columns': 1,
                 'owner': '',
                 'painters': [('service_state', None),
                              ('host', 'host'),
                              ('service_description', 'service'),
                              ('service_icons', None),
                              ('svc_plugin_output', None),
                              ('svc_state_age', None),
                              ('svc_check_age', None),
                              # ('perfometer', None),
                              ],
                 'play_sounds': True,
                 'public': True,
                 'show_filters': [],
                 'sorters': [('svcstate', True),
                             ('stateage', False),
                             ('svcdescr', False)],
                 'title': 'Service problems',
                  'topic': None
                },
# Similar view, but for dashboard
'events_dash': {
            'browser_reload': 90,
            'column_headers': 'pergroup',
            'datasource': 'log_events',
            'description': 'Events of the last 4 hours.',
            'group_painters': [],
            'hard_filters': ['logtime'],
            'hard_filtervars': [
                                ('logtime_from_range', '3600'),
                                ('logtime_from', '4'),
                                ],
            'hidden': False,
            'hide_filters': [],
            'layout': 'table',
            'linktitle': 'Events',
            'mustsearch': False,
            'name': 'events_dash',
            'num_columns': 1,
            'owner': 'admin',
            'painters': [('log_icon', None),
                         ('log_time', None),
                         # ('log_type', None),
                         ('host', 'hostsvcevents'),
                         ('service_description', 'svcevents'),
                         # ('log_state_type', None),
                         ('log_plugin_output', None)],


            'play_sounds': False,
            'public': True,
            'show_filters': [],
            'sorters': [],
            'title': 'Events of the last 4 hours (for the dashboard)',
            'topic': None},
})


