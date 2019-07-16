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
from cmk.gui.globals import html
from cmk.gui.htmllib import HTML

from cmk.gui.plugins.views import (
    multisite_builtin_views,
    layout_registry,
    Layout,
    PainterOptions,
)

#   .--Views---------------------------------------------------------------.
#   |                    __     ___                                        |
#   |                    \ \   / (_) _____      _____                      |
#   |                     \ \ / /| |/ _ \ \ /\ / / __|                     |
#   |                      \ V / | |  __/\ V  V /\__ \                     |
#   |                       \_/  |_|\___| \_/\_/ |___/                     |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Views optimated for usage in the mobile UI                           |
#   '----------------------------------------------------------------------'


def mobile_view(d):
    x = {
        'mobile': True,
        'browser_reload': 0,
        'column_headers': 'perpage',
        'description': 'This view is used by the mobile GUI',
        'hidden': False,
        'hidebutton': False,
        'icon': None,
        'public': True,
        'topic': _('Mobile'),
        'user_sortable': False,
        'play_sounds': False,
        'show_checkboxes': False,
        'mustsearch': False,
    }
    x.update(d)
    return x


multisite_builtin_views.update({

    #Service search
    'mobile_searchsvc': mobile_view({
        'datasource': 'services',
        'group_painters': [('sitealias', 'sitehosts'), ('host', 'host')],
        'hard_filters': [],
        'hard_filtervars': [
            ('is_service_in_notification_period', '-1'),
            ('optservicegroup', ''),
            ('is_service_notifications_enabled', '-1'),
            ('is_host_in_notification_period', '-1'),
            ('is_in_downtime', '-1'),
            ('is_service_scheduled_downtime_depth', '-1'),
            ('is_service_acknowledged', '-1'),
            ('host', ''),
            ('is_service_active_checks_enabled', '-1'),
            ('service', ''),
            ('check_command', ''),
            ('st0', 'on'),
            ('st1', 'on'),
            ('st2', 'on'),
            ('st3', 'on'),
            ('stp', 'on'),
            ('opthostgroup', ''),
            ('service_output', ''),
            ('is_service_is_flapping', '-1'),
        ],
        'hide_filters': [],
        'layout': 'mobilelist',
        'mustsearch': True,
        'name': 'mobile_searchsvc',
        'num_columns': 2,
        'owner': '',
        'painters': [
            ('service_state', None, ''),
            ('host', 'mobile_hoststatus', ''),
            ('service_description', 'mobile_service', ''),
            ('svc_plugin_output', ''),
            ('svc_state_age', None, ''),
        ],
        'public': True,
        'show_filters': [
            'service_in_notification_period',
            'service_notifications_enabled',
            'host_in_notification_period',
            'in_downtime',
            'service_scheduled_downtime_depth',
            'service_acknowledged',
            'hostregex',
            'serviceregex',
            'hoststate',
            'svcstate',
            'svchardstate',
            'opthostgroup',
            'output',
        ],
        'sorters': [
            ('site', False),
            ('site_host', False),
            ('svcdescr', False),
        ],
        'title': _('Search'),
        'topic': _('Services')
    }),

    # View of all current service problems
    'mobile_svcproblems': mobile_view({
        'datasource': 'services',
        'group_painters': [],
        'hard_filters': ['in_downtime'],
        'hard_filtervars': [
            ('is_in_downtime', '0'),
            ('st0', ''),
            ('st1', 'on'),
            ('st2', 'on'),
            ('st3', 'on'),
            ('stp', ''),
            ('hst0', 'on'),
            ('hst1', ''),
            ('hst2', ''),
            ('hstp', 'on'),
        ],
        'hide_filters': [],
        'layout': 'mobilelist',
        'name': 'mobile_svcproblems',
        'num_columns': 2,
        'painters': [
            ('service_state', None, ''),
            ('host', 'mobile_hoststatus', ''),
            ('service_description', 'mobile_service', ''),
            ('svc_plugin_output', ''),
            ('svc_state_age', None, ''),
        ],
        'show_filters': [
            'service_in_notification_period',
            'service_acknowledged',
            'svcstate',
            'svchardstate',
            'hoststate',
        ],
        'sorters': [
            ('svcstate', True),
            ('stateage', False),
            ('svcdescr', False),
        ],
        'title': _('Problems (all)'),
        'topic': _('Services'),
    }),

    # View of unhandled service problems
    'mobile_svcproblems_unack': mobile_view({
        'datasource': 'services',
        'group_painters': [],
        'hard_filters': ['in_downtime', 'service_acknowledged'],
        'hard_filtervars': [
            ('is_service_in_notification_period', '-1'),
            ('hst0', 'on'),
            ('hst1', ''),
            ('hst2', ''),
            ('hstp', 'on'),
            ('is_service_acknowledged', '0'),
            ('hdst0', 'on'),
            ('hdst1', 'on'),
            ('hdst2', 'on'),
            ('hdst3', 'on'),
            ('hdstp', 'on'),
            ('st0', ''),
            ('st1', 'on'),
            ('st2', 'on'),
            ('st3', 'on'),
            ('stp', ''),
            ('is_in_downtime', '0'),
        ],
        'hide_filters': [],
        'layout': 'mobilelist',
        'name': 'mobile_svcproblems_unack',
        'num_columns': 2,
        'painters': [
            ('service_state', None, ''),
            ('host', 'mobile_hoststatus', ''),
            ('service_description', 'mobile_service', ''),
            ('svc_plugin_output', ''),
            ('svc_state_age', None, ''),
        ],
        'show_filters': [
            'service_in_notification_period',
            'hoststate',
            'svchardstate',
            'svcstate',
        ],
        'sorters': [
            ('svcstate', True),
            ('stateage', False),
            ('svcdescr', False),
        ],
        'linktitle': _('Problems (unhandled)'),
        'title': _('Problems (unhandled)'),
        'topic': _('Services'),
    }),

    # Service details
    'mobile_service': mobile_view({
        'datasource': 'services',
        'group_painters': [],
        'hard_filters': [],
        'hard_filtervars': [],
        'hide_filters': ['site', 'service', 'host'],
        'layout': 'mobiledataset',
        'linktitle': 'Details',
        'name': 'mobile_service',
        'num_columns': 1,
        'hidden': True,
        'painters': [
            ('sitealias', None, ''),
            ('host', 'mobile_host', ''),
            ('service_description', ''),
            ('svc_plugin_output', None, ''),
            ('service_icons', None, ''),
            ('service_state', None, ''),
            ('svc_state_age', None, ''),
            ('svc_check_age', None, ''),
            ('svc_group_memberlist', None, ''),
            ('svc_contact_groups', None, ''),
            ('svc_contacts', None, ''),
            ('svc_long_plugin_output', None, ''),
            ('svc_perf_data', None, ''),
            ('svc_check_command', None, ''),
            ('svc_attempt', None, ''),
            ('svc_check_type', None, ''),
            ('svc_next_check', None, ''),
            ('svc_next_notification', None, ''),
            ('svc_last_notification', None, ''),
            ('svc_check_latency', None, ''),
            ('svc_check_duration', None, ''),
            ('svc_in_downtime', None, ''),
            ('svc_in_notifper', None, ''),
            ('svc_notifper', None, ''),
            ('svc_custom_notes', None, ''),
            ('svc_pnpgraph', None, ''),
        ],
        'show_filters': [],
        'sorters': [],
        'title': _('Service'),
    }),

    # All services of one host
    'mobile_host': mobile_view({
        'datasource': 'services',
        'group_painters': [],
        'hard_filters': [],
        'hard_filtervars': [
            ('st0', 'on'),
            ('st1', 'on'),
            ('st2', 'on'),
            ('st3', 'on'),
            ('stp', 'on'),
        ],
        'hidden': True,
        'hide_filters': ['site', 'host'],
        'layout': 'mobilelist',
        'name': 'mobile_svcproblems',
        'num_columns': 1,
        'painters': [
            ('service_state', None),
            ('service_description', 'mobile_service'),
            ('svc_plugin_output', None),
            ('svc_state_age', None),
        ],
        'show_filters': ['svcstate', 'serviceregex'],
        'sorters': [('svcstate', True), ('stateage', False), ('svcdescr', False)],
        'linktitle': _('Services of this host'),
        'title': _('Services of host'),
    }),

    # Host details
    'mobile_hoststatus': mobile_view({
        'datasource': 'hosts',
        'group_painters': [],
        'hard_filters': [],
        'hard_filtervars': [],
        'hide_filters': ['site', 'host'],
        'icon': 'status',
        'layout': 'mobiledataset',
        'hidden': True,
        'painters': [
            ('sitealias', None),
            ('host', 'mobile_host'),
            ('alias', None),
            ('host_icons', None),
            ('host_state', None),
            ('host_address', None),
            ('host_parents', None),
            ('host_childs', None),
            ('host_contact_groups', None),
            ('host_contacts', None),
            ('host_plugin_output', None),
            ('host_perf_data', None),
            ('host_attempt', None),
            ('host_check_type', None),
            ('host_state_age', None),
            ('host_check_age', None),
            ('host_next_check', None),
            ('host_next_notification', None),
            ('host_last_notification', None),
            ('host_check_latency', None),
            ('host_check_duration', None),
            ('host_in_downtime', None),
            ('host_in_notifper', None),
            ('host_notifper', None),
            ('num_services', 'mobile_host'),
            ('host_pnpgraph', None),
        ],
        'show_filters': [],
        'sorters': [],
        'title': _('Host status'),
    }),

    # Search hosts
    'mobile_searchhost': mobile_view({
        'datasource': 'hosts',
        'group_painters': [],
        'hard_filters': [],
        'hard_filtervars': [
            ('is_host_scheduled_downtime_depth', '-1'),
            ('is_host_in_notification_period', '-1'),
            ('hst0', 'on'),
            ('hst1', 'on'),
            ('hst2', 'on'),
            ('hstp', 'on'),
            ('site', ''),
            ('host', ''),
            ('is_host_notifications_enabled', '-1'),
            ('opthostgroup', ''),
            ('neg_opthostgroup', ''),
            ('opthost_contactgroup', ''),
            ('neg_opthost_contactgroup', ''),
        ],
        'hide_filters': [],
        'layout': 'mobilelist',
        'linktitle': 'Host search',
        'mustsearch': True,
        'num_columns': 2,
        'painters': [
            ('host_state', None),
            ('host', 'mobile_host'),
            ('host_plugin_output', None),
        ],
        'show_filters': [
            'hoststate',
            'hostregex',
            'opthostgroup',
        ],
        'sorters': [],
        'title': _('Search'),
        'topic': _('Hosts'),
    }),

    #List all host problems
    'mobile_hostproblems': mobile_view({
        'datasource': 'hosts',
        'group_painters': [('host_state', None)],
        'hard_filters': ['host_scheduled_downtime_depth'],
        'hard_filtervars': [
            ('is_host_scheduled_downtime_depth', '0'),
            ('is_host_in_notification_period', '-1'),
            ('hst0', ''),
            ('hst1', 'on'),
            ('hst2', 'on'),
            ('hstp', ''),
            ('is_host_acknowledged', '-1'),
            ('host', ''),
            ('opthostgroup', ''),
        ],
        'hide_filters': [],
        'layout': 'mobilelist',
        'mustsearch': False,
        'name': 'hostproblems',
        'num_columns': 2,
        'painters': [
            ('host_state', None),
            ('host', 'mobile_host'),
            ('host_plugin_output', None),
        ],
        'public': True,
        'show_filters': [
            'host_in_notification_period',
            'hoststate',
            'hostregex',
            'opthostgroup',
            'host_acknowledged',
        ],
        'sorters': [],
        'title': _('Problems (all)'),
        'topic': _('Hosts')
    }),

    #List unhandled host problems
    'mobile_hostproblems_unack': mobile_view({
        'datasource': 'hosts',
        'group_painters': [('host_state', None)],
        'hard_filters': ['host_scheduled_downtime_depth', 'host_acknowledged'],
        'hard_filtervars': [
            ('is_host_scheduled_downtime_depth', '0'),
            ('is_host_in_notification_period', '-1'),
            ('hst0', ''),
            ('hst1', 'on'),
            ('hst2', 'on'),
            ('hstp', ''),
            ('is_host_acknowledged', '0'),
            ('host', ''),
            ('opthostgroup', ''),
        ],
        'hide_filters': [],
        'layout': 'mobilelist',
        'mustsearch': False,
        'name': 'hostproblems',
        'num_columns': 2,
        'painters': [
            ('host_state', None),
            ('host', 'mobile_host'),
            ('host_plugin_output', None),
        ],
        'public': True,
        'show_filters': [
            'host_in_notification_period',
            'hoststate',
            'hostregex',
            'opthostgroup',
        ],
        'sorters': [],
        'title': _('Problems (unhandled)'),
        'topic': _('Hosts')
    }),

    # All Nagios Events at all
    'mobile_events': mobile_view({
        'datasource': 'log_events',
        'group_painters': [],
        'hard_filters': ['logtime'],
        'hard_filtervars': [
            ('logtime_from_range', '3600'),
            ('logtime_from', '4'),
        ],
        'hide_filters': [],
        'layout': 'mobilelist',
        'linktitle': 'Events',
        'mustsearch': False,
        'name': 'mobile_events',
        'num_columns': 1,
        'painters': [
            ('log_icon', None),
            ('log_time', None),
            ('host', 'mobile_hostsvcevents'),
            ('service_description', 'mobile_svcevents'),
            ('log_plugin_output', None),
        ],
        'public': True,
        'show_filters': [],
        'sorters': [('log_time', False), ('log_lineno', False)],
        'title': 'Events',
        'topic': _('Events')
    }),

    # All Notifications at all
    'mobile_notifications': mobile_view({
        'datasource': 'log',
        'group_painters': [('log_date', None, '')],
        'hard_filters': ['log_class'],
        'hard_filtervars': [
            ('logclass0', ''),
            ('logclass1', ''),
            ('logclass2', ''),
            ('logclass3', 'on'),
            ('logclass4', ''),
            ('logclass5', ''),
            ('logclass6', ''),
            ('host', ''),
            ('service', ''),
            ('log_plugin_output', ''),
            ('logtime_from_range', '3600'),
            ('logtime_from', '24'),
        ],
        'hide_filters': [],
        'icon': 'notification',
        'layout': 'mobilelist',
        'linktitle': _('Notifications'),
        'mustsearch': False,
        'name': 'mobile_notifications',
        'num_columns': 2,
        'painters': [
            ('log_state', None, ''),
            ('host', 'mobile_hostsvcnotifications', ''),
            ('service_description', 'mobile_svcnotifications', ''),
            ('log_time', None, ''),
            ('log_contact_name', 'mobile_contactnotifications', ''),
            ('log_type', None, ''),
            ('log_plugin_output', None, ''),
        ],
        'public': True,
        'show_filters': [
            'hostregex',
            'serviceregex',
            'log_plugin_output',
            'logtime',
        ],
        'sorters': [('log_time', False), ('log_lineno', False)],
        'title': _('Notifications'),
        'topic': _('Events')
    }),

    # All events of a Host
    'mobile_hostsvcevents': mobile_view({
        'browser_reload': 0,
        'datasource': 'log_events',
        'group_painters': [('log_date', None)],
        'hard_filters': [],
        'hard_filtervars': [
            ('logtime_from_range', '86400'),
            ('logtime_from', '7'),
        ],
        'hidden': True,
        'hide_filters': ['site', 'host'],
        'icon': 'history',
        'layout': 'mobilelist',
        'linktitle': _('Host+Svc history'),
        'name': 'events',
        'num_columns': 2,
        'painters': [
            ('log_icon', None),
            ('log_time', None),
            ('log_type', None),
            ('host', None),
            ('service_description', 'mobile_svcevents'),
            ('log_state_type', None),
            ('log_plugin_output', None),
        ],
        'show_filters': ['logtime', 'log_state'],
        'sorters': [('log_time', False), ('log_lineno', False)],
        'title': _('Events of host & services')
    }),

    # All events of one service
    'mobile_svcevents': mobile_view({
        'browser_reload': 0,
        'datasource': 'log_events',
        'group_painters': [('log_date', None)],
        'hard_filters': [],
        'hard_filtervars': [
            ('logtime_from_range', '86400'),
            ('logtime_from', '7'),
        ],
        'hidden': True,
        'hide_filters': ['site', 'host', 'service'],
        'icon': 'history',
        'layout': 'mobilelist',
        'linktitle': _('History'),
        'name': 'events',
        'num_columns': 2,
        'painters': [
            ('log_icon', None),
            ('log_time', None),
            ('log_type', None),
            ('log_state_type', None),
            ('log_plugin_output', None),
        ],
        'show_filters': ['logtime'],
        'sorters': [('log_time', False), ('log_lineno', False)],
        'title': _('Events of service')
    }),

    # All Notfications of a contact
    'mobile_contactnotifications': mobile_view({
        'datasource': 'log',
        'group_painters': [('log_date', None, '')],
        'hard_filters': ['log_class'],
        'hard_filtervars': [
            ('logclass0', ''),
            ('logclass1', ''),
            ('logclass2', ''),
            ('logclass3', 'on'),
            ('logclass4', ''),
            ('logclass5', ''),
            ('logclass6', ''),
            ('host', ''),
            ('service', ''),
            ('log_plugin_output', ''),
            ('logtime_from_range', '86400'),
            ('logtime_from', '7'),
        ],
        'hidden': True,
        'hide_filters': ['log_contact_name'],
        'hidebutton': False,
        'icon': 'notification',
        'layout': 'mobilelist',
        'linktitle': _('Contact notification'),
        'name': 'mobile_contactnotifications',
        'num_columns': 2,
        'painters': [
            ('log_time', None, ''),
            ('host', 'mobile_hostsvcnotifications', ''),
            ('service_description', 'mobile_svcnotifications', ''),
            ('log_type', None, ''),
            ('log_state', None, ''),
            ('log_plugin_output', None, ''),
        ],
        'public': True,
        'show_filters': ['host', 'serviceregex', 'log_plugin_output', 'logtime'],
        'sorters': [('log_time', False), ('log_lineno', False)],
        'title': _('Notifications of contact'),
        'topic': _('Other')
    }),

    # All Notfications of Host
    'mobile_hostsvcnotifications': mobile_view({
        'datasource': 'log',
        'group_painters': [('log_date', None, '')],
        'hard_filters': ['log_class'],
        'hard_filtervars': [
            ('logclass0', ''),
            ('logclass1', ''),
            ('logclass2', ''),
            ('logclass3', 'on'),
            ('logclass4', ''),
            ('logclass5', ''),
            ('logclass6', ''),
            ('service', ''),
            ('log_plugin_output', ''),
            ('logtime_from_range', '86400'),
            ('logtime_from', '7'),
        ],
        'hidden': True,
        'hide_filters': ['site', 'host'],
        'hidebutton': False,
        'icon': 'notification',
        'layout': 'mobilelist',
        'linktitle': _('Host+Svc notifications'),
        'name': 'hostsvcnotifications',
        'num_columns': 2,
        'painters': [
            ('log_time', None, ''),
            ('log_contact_name', 'mobile_contactnotifications', ''),
            ('log_type', None, ''),
            ('host', 'mobile_hostsvcnotifications', ''),
            ('service_description', 'mobile_svcnotifications', ''),
            ('log_state', None, ''),
            ('log_plugin_output', None, ''),
        ],
        'show_filters': ['serviceregex', 'log_plugin_output', 'logtime'],
        'sorters': [('log_time', False), ('log_lineno', False)],
        'title': _('Notifications of host & services'),
        'topic': _('Other')
    }),

    # All Notfications of a service
    'mobile_svcnotifications': mobile_view({
        'datasource': 'log',
        'group_painters': [('log_date', None, '')],
        'hard_filters': ['log_class'],
        'hard_filtervars': [
            ('logclass0', ''),
            ('logclass1', ''),
            ('logclass2', ''),
            ('logclass3', 'on'),
            ('logclass4', ''),
            ('logclass5', ''),
            ('logclass6', ''),
            ('log_plugin_output', ''),
            ('logtime_from_range', '86400'),
            ('logtime_from', '7'),
        ],
        'hidden': True,
        'hide_filters': ['site', 'service', 'host'],
        'hidebutton': False,
        'icon': 'notification',
        'layout': 'mobilelist',
        'linktitle': _('Notifications'),
        'name': 'mobile_svcnotifications',
        'num_columns': 2,
        'painters': [
            ('log_time', None, ''),
            ('log_contact_name', 'mobile_contactnotifications', ''),
            ('host', None, ''),
            ('log_state', None, ''),
            ('log_plugin_output', None, ''),
        ],
        'play_sounds': False,
        'public': True,
        'show_filters': ['log_plugin_output', 'logtime'],
        'sorters': [('log_time', False), ('log_lineno', False)],
        'title': _('Service Notifications'),
        'topic': _('Other')
    }),
})

#.
#   .--Layouts-------------------------------------------------------------.
#   |                _                            _                        |
#   |               | |    __ _ _   _  ___  _   _| |_ ___                  |
#   |               | |   / _` | | | |/ _ \| | | | __/ __|                 |
#   |               | |__| (_| | |_| | (_) | |_| | |_\__ \                 |
#   |               |_____\__,_|\__, |\___/ \__,_|\__|___/                 |
#   |                           |___/                                      |
#   +----------------------------------------------------------------------+
#   | Display-Layouts for the views used by mobile. There are two layouts: |
#   | one for a list of items, one for a single dataset.                   |
#   '----------------------------------------------------------------------'


def render_mobile_table(rows, view, group_cells, cells, num_columns, show_checkboxes):
    if not html.mobile:
        html.show_error(_("This view can only be used in mobile mode."))
        return

    # Force relative timestamp always. This saves space.
    painter_options = PainterOptions.get_instance()
    painter_options.set("ts_format", "rel")

    odd = "odd"
    html.open_table(class_="mobile data")

    # Paint header
    if view.get("column_headers") != "off":
        html.open_tr()
        n = 0
        for cell in cells:
            cell.paint_as_header()
        html.close_tr()

    # Paint data rows
    for row in rows:
        odd = "even" if odd == "odd" else "odd"
        html.open_tr(class_="%s0" % odd)
        for n, cell in enumerate(cells):
            if n > 0 and n % num_columns == 0:
                html.close_tr()
                html.open_tr(class_="%s0" % odd)
            if n == len(cells) - 1 and n % num_columns != (num_columns - 1):
                tdattrs = 'colspan="%d"' % (num_columns - (n % num_columns))
            else:
                tdattrs = ""
            cell.paint(row, tdattrs=tdattrs)
        html.close_row()
    html.close_table()
    html.javascript('$("table.mobile a").attr("data-ajax", "false");')


@layout_registry.register
class LayoutMobileTable(Layout):
    @property
    def ident(self):
        return "mobiletable"

    @property
    def title(self):
        return _("Mobile: Table")

    @property
    def can_display_checkboxes(self):
        return False

    @property
    def is_hidden(self):
        return False

    def render(self, rows, view, group_cells, cells, num_columns, show_checkboxes):
        # TODO: Move to class
        render_mobile_table(rows, view, group_cells, cells, num_columns, show_checkboxes)


def render_mobile_list(rows, view, group_cells, cells, num_columns, show_checkboxes):
    if not html.mobile:
        html.show_error(_("This view can only be used in mobile mode."))
        return

    # Force relative timestamp always. This saves space.
    painter_options = PainterOptions.get_instance()
    painter_options.set("ts_format", "rel")

    html.open_ul(class_="mobilelist", **{"data-role": "listview"})

    # Paint data rows
    for row in rows:
        html.open_li()
        rendered_cells = [cell.render(row) for cell in cells]
        if rendered_cells:  # First cell (assumedly state) is left
            rendered_class, rendered_content = rendered_cells[0]
            html.open_p(class_=["ui-li-aside", "ui-li-desc", rendered_class])
            html.write(rendered_content)
            html.close_p()

            if len(rendered_cells) > 1:
                content = HTML(" &middot; ").join(
                    [rendered_cell[1] for rendered_cell in rendered_cells[1:num_columns + 1]])
                html.h3(content)

                for rendered_cell, cell in zip(rendered_cells[num_columns + 1:],
                                               cells[num_columns + 1:]):
                    rendered_class, rendered_content = rendered_cell
                    html.open_p(class_="ui-li-desc")
                    cell.paint_as_header()
                    html.write_text(': ')
                    html.open_span(class_=rendered_class)
                    html.write(rendered_content)
                    html.close_span()
                    html.close_p()

        html.close_li()
    html.close_ul()
    html.javascript('$("ul.mobilelist a").attr("data-ajax", "false");')


@layout_registry.register
class LayoutMobileList(Layout):
    @property
    def ident(self):
        return "mobilelist"

    @property
    def title(self):
        return _("Mobile: List")

    @property
    def can_display_checkboxes(self):
        return False

    @property
    def is_hidden(self):
        return False

    def render(self, rows, view, group_cells, cells, num_columns, show_checkboxes):
        # TODO: Move to class
        render_mobile_list(rows, view, group_cells, cells, num_columns, show_checkboxes)


def render_mobile_dataset(rows, view, group_cells, cells, num_columns, show_checkboxes):
    if not html.mobile:
        html.show_error(_("This view can only be used in mobile mode."))
        return

    painter_options = PainterOptions.get_instance()
    painter_options.set("ts_format", "both")

    for row in rows:
        html.open_table(class_="dataset")
        for cell in cells:
            _tdclass, content = cell.render(row)
            if not content:
                continue  # Omit empty cells

            html.open_tr(class_="header")
            html.open_th()
            html.write(cell.title())
            html.close_th()
            html.close_tr()

            html.open_tr(class_="data")
            cell.paint(row)
            html.close_tr()

        html.close_table()
    html.javascript(
        '$("table.dataset > tbody > tr.data > td").addClass("ui-shadow").not(".state").addClass("nonstatus");\n'
        '$("table.dataset > tbody > tr.data a").attr("data-ajax", "false");\n')


@layout_registry.register
class LayoutMobileDataset(Layout):
    @property
    def ident(self):
        return "mobiledataset"

    @property
    def title(self):
        return _("Mobile: Dataset")

    @property
    def can_display_checkboxes(self):
        return False

    @property
    def is_hidden(self):
        return False

    def render(self, rows, view, group_cells, cells, num_columns, show_checkboxes):
        # TODO: Move to class
        render_mobile_dataset(rows, view, group_cells, cells, num_columns, show_checkboxes)
