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

from cmk.gui.i18n import _
from . import (
    multisite_builtin_views,)

multisite_builtin_views.update({
    'topology_filters': {
        'browser_reload': 30,
        'column_headers': 'pergroup',
        'datasource': 'hosts',
        'description':
            _('Configures the number of available filters in the network topology view.'),
        'group_painters': [],
        'hard_filters': [],
        'hard_filtervars': [],
        'hidden': True,
        'hide_filters': [],
        'layout': 'table',
        'mustsearch': False,
        'name': 'allhosts',
        'num_columns': 3,
        'owner': '',
        'painters': [('host_state', None)],
        'play_sounds': False,
        'public': True,
        'show_filters': [
            'hoststate',
            'hostalias',
            'siteopt',
            'hostregex',
            'hostgroups',
            'host_labels',
            'opthost_contactgroup',
            'host_tags',
        ],
        'sorters': [],
        'title': _('Topology filters'),
        'topic': _('Topology'),
    },
    'bi_map_hover_host': {
        'browser_reload': 0,
        'column_headers': 'pergroup',
        'datasource': 'hosts',
        'description': _("Host hover menu shown in BI visualization"),
        'hidden': True,
        'hidebutton': True,
        'hide_filters': [],
        'hard_filters': [],
        'hard_filtervars': [],
        'show_filters': [],
        'group_painters': [],
        'icon': None,
        'layout': 'dataset',
        'linktitle': u'Hover Host',
        'mobile': False,
        'mustsearch': False,
        'name': 'bi_map_hover_host',
        'num_columns': 1,
        'owner': '',
        'painters': [(('host', {
            'color_choices': []
        }), 'hoststatus', None), ('host_state', None, None), ('host_plugin_output', None, None)],
        'play_sounds': False,
        'public': True,
        'single_infos': ['host'],
        'sorters': [],
        'title': _('BI host details'),
    },
    'bi_map_hover_service': {
        'browser_reload': 0,
        'column_headers': 'pergroup',
        'datasource': 'services',
        'description': _("Service hover menu shown in BI visualization"),
        'hidden': True,
        'hidebutton': True,
        'hide_filters': [],
        'hard_filters': [],
        'hard_filtervars': [],
        'show_filters': [],
        'group_painters': [],
        'icon': None,
        'layout': 'dataset',
        'linktitle': u'Hover service',
        'mobile': False,
        'mustsearch': False,
        'name': 'bi_map_hover_service',
        'num_columns': 1,
        'painters': [(('host', {
            'color_choices': []
        }), 'hoststatus', None), ('service_description', 'service', None),
                     ('service_state', None, None), ('host_check_age', None, None),
                     ('svc_acknowledged', None, None), ('svc_in_downtime', None, None)],
        'play_sounds': False,
        'public': True,
        'single_infos': ['service', 'host'],
        'sorters': [],
        'title': _("BI service details"),
    },
    'topology_hover_host': {
        'browser_reload': 0,
        'column_headers': 'pergroup',
        'datasource': 'hosts',
        'description': _("Host hover menu shown in topolgoy visualization"),
        'hidden': True,
        'hidebutton': True,
        'hide_filters': [],
        'hard_filters': [],
        'hard_filtervars': [],
        'show_filters': [],
        'group_painters': [],
        'icon': None,
        'layout': 'dataset',
        'linktitle': u'Hover Host',
        'mobile': False,
        'mustsearch': False,
        'name': 'topology_hover_host',
        'num_columns': 1,
        'owner': '',
        'painters': [(('host', {
            'color_choices': []
        }), 'hoststatus', None), ('host_state', None, None), ('host_plugin_output', None, None),
                     ("host_parents", None, None), ("host_childs", None, None)],
        'play_sounds': False,
        'public': True,
        'single_infos': ['host'],
        'sorters': [],
        'title': _('Topology host details'),
    },
})
