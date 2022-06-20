#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable

from cmk.gui.plugins.visuals.utils import Filter
import copy
from typing import Any, Dict, Tuple

import pytest  # type: ignore[import]

import cmk.gui.config as config
import cmk.utils.version as cmk_version
from cmk.utils.livestatus_helpers.testing import MockLiveStatusConnection

pytestmark = pytest.mark.usefixtures("load_plugins")

from cmk.gui.globals import html
from cmk.gui.valuespec import ValueSpec
import cmk.gui.plugins.views
from cmk.gui.plugins.views.utils import transform_painter_spec
from cmk.gui.type_defs import PainterSpec
import cmk.gui.views
from cmk.gui.plugins.views import Cell, Painter


@pytest.fixture(name="view")
def view_fixture(register_builtin_html):
    view_name = "allhosts"
    view_spec = transform_painter_spec(cmk.gui.views.multisite_builtin_views[view_name].copy())
    return cmk.gui.views.View(view_name, view_spec, view_spec.get("context", {}))


def test_registered_painter_options():
    expected = [
        'aggr_expand',
        'aggr_onlyproblems',
        'aggr_treetype',
        'aggr_wrap',
        'matrix_omit_uniform',
        'pnp_timerange',
        'show_internal_tree_paths',
        'ts_date',
        'ts_format',
        'graph_render_options',
        "refresh",
        "num_columns",
    ]

    names = cmk.gui.plugins.views.painter_option_registry.keys()
    assert sorted(expected) == sorted(names)

    for cls in cmk.gui.plugins.views.painter_option_registry.values():
        vs = cls().valuespec
        assert isinstance(vs, ValueSpec)


def test_registered_layouts():
    expected = [
        'boxed',
        'boxed_graph',
        'dataset',
        'matrix',
        'mobiledataset',
        'mobilelist',
        'mobiletable',
        'table',
        'tiled',
    ]

    names = cmk.gui.plugins.views.layout_registry.keys()
    assert sorted(expected) == sorted(names)


def test_layout_properties():
    expected = {
        'boxed': {
            'checkboxes': True,
            'title': u'Balanced boxes'
        },
        'boxed_graph': {
            'checkboxes': True,
            'title': u'Balanced graph boxes'
        },
        'dataset': {
            'checkboxes': False,
            'title': u'Single dataset'
        },
        'matrix': {
            'checkboxes': False,
            'has_csv_export': True,
            'options': ['matrix_omit_uniform'],
            'title': u'Matrix'
        },
        'mobiledataset': {
            'checkboxes': False,
            'title': u'Mobile: Dataset'
        },
        'mobilelist': {
            'checkboxes': False,
            'title': u'Mobile: List'
        },
        'mobiletable': {
            'checkboxes': False,
            'title': u'Mobile: Table'
        },
        'table': {
            'checkboxes': True,
            'title': u'Table'
        },
        'tiled': {
            'checkboxes': True,
            'title': u'Tiles'
        },
    }

    for ident, spec in expected.items():
        plugin = cmk.gui.plugins.views.layout_registry[ident]()
        assert isinstance(plugin.title, str)
        assert spec["title"] == plugin.title
        assert spec["checkboxes"] == plugin.can_display_checkboxes
        assert spec.get("has_csv_export", False) == plugin.has_individual_csv_export


def test_get_layout_choices():
    choices = cmk.gui.plugins.views.layout_registry.get_choices()
    assert sorted(choices) == sorted([
        ('matrix', u'Matrix'),
        ('boxed_graph', u'Balanced graph boxes'),
        ('dataset', u'Single dataset'),
        ('tiled', u'Tiles'),
        ('table', u'Table'),
        ('boxed', u'Balanced boxes'),
        ('mobiledataset', u'Mobile: Dataset'),
        ('mobiletable', u'Mobile: Table'),
        ('mobilelist', u'Mobile: List'),
    ])


def test_registered_exporters():
    expected = [
        'csv',
        'csv_export',
        'json',
        'json_export',
        'jsonp',
        'python',
        'python-raw',
    ]
    names = cmk.gui.plugins.views.exporter_registry.keys()
    assert sorted(expected) == sorted(names)


def test_registered_command_groups():
    expected = [
        'acknowledge',
        'downtimes',
        'fake_check',
        'various',
    ]

    names = cmk.gui.plugins.views.utils.command_group_registry.keys()
    assert sorted(expected) == sorted(names)


def test_legacy_register_command_group(monkeypatch):
    monkeypatch.setattr(cmk.gui.plugins.views.utils, "command_group_registry",
                        cmk.gui.plugins.views.utils.CommandGroupRegistry())
    cmk.gui.plugins.views.utils.register_command_group("abc", "A B C", 123)

    group = cmk.gui.plugins.views.utils.command_group_registry["abc"]()
    assert isinstance(group, cmk.gui.plugins.views.utils.CommandGroup)
    assert group.ident == "abc"
    assert group.title == "A B C"
    assert group.sort_index == 123


def test_registered_commands():
    expected: Dict[str, Dict[str, Any]] = {
        'acknowledge': {
            'group': 'acknowledge',
            'permission': 'action.acknowledge',
            'tables': ['host', 'service', 'aggr'],
            'title': u'Acknowledge problems'
        },
        'ec_custom_actions': {
            'permission': 'mkeventd.actions',
            'tables': ['event'],
            'title': u'Custom Action'
        },
        'remove_comments': {
            'permission': 'action.addcomment',
            'tables': ['comment'],
            'title': u'Remove comments'
        },
        'remove_downtimes': {
            'permission': 'action.downtimes',
            'tables': ['downtime'],
            'title': u'Remove downtimes'
        },
        'schedule_downtimes': {
            'permission': 'action.downtimes',
            'tables': ['host', 'service', 'aggr'],
            'title': u'Schedule downtimes'
        },
        'ec_archive_events_of_host': {
            'permission': 'mkeventd.archive_events_of_hosts',
            'tables': ['service'],
            'title': u'Archive events of hosts'
        },
        'ec_change_state': {
            'permission': 'mkeventd.changestate',
            'tables': ['event'],
            'title': u'Change State'
        },
        'clear_modified_attributes': {
            'permission': 'action.clearmodattr',
            'tables': ['host', 'service'],
            'title': u'Modified attributes'
        },
        'send_custom_notification': {
            'permission': 'action.customnotification',
            'tables': ['host', 'service'],
            'title': u'Custom notification'
        },
        'ec_archive_event': {
            'permission': 'mkeventd.delete',
            'tables': ['event'],
            'title': u'Archive Event'
        },
        'add_comment': {
            'permission': 'action.addcomment',
            'tables': ['host', 'service'],
            'title': u'Add comment'
        },
        'toggle_passive_checks': {
            'permission': 'action.enablechecks',
            'tables': ['host', 'service'],
            'title': u'Passive checks'
        },
        'toggle_active_checks': {
            'permission': 'action.enablechecks',
            'tables': ['host', 'service'],
            'title': u'Active checks'
        },
        'fake_check_result': {
            'group': 'fake_check',
            'permission': 'action.fakechecks',
            'tables': ['host', 'service'],
            'title': u'Fake check results'
        },
        'notifications': {
            'permission': 'action.notifications',
            'tables': ['host', 'service'],
            'title': u'Notifications'
        },
        'reschedule': {
            'permission': 'action.reschedule',
            'row_stats': True,
            'tables': ['host', 'service'],
            'title': u'Reschedule active checks'
        },
        'favorites': {
            'permission': 'action.star',
            'tables': ['host', 'service'],
            'title': u'Favorites'
        },
        'ec_update_event': {
            'permission': 'mkeventd.update',
            'tables': ['event'],
            'title': u'Update & Acknowledge'
        },
        'delete_crash_reports': {
            'permission': 'action.delete_crash_report',
            'tables': ['crash'],
            'title': u'Delete crash reports',
        },
    }

    if not cmk_version.is_raw_edition():
        expected.update({'edit_downtimes': {
            'permission': 'action.downtimes',
            'tables': ['downtime'],
            'title': u'Edit Downtimes'
        },
        })

    names = cmk.gui.plugins.views.command_registry.keys()
    assert sorted(expected.keys()) == sorted(names)

    for cmd_class in cmk.gui.plugins.views.utils.command_registry.values():
        cmd = cmd_class()
        cmd_spec = expected[cmd.ident]
        assert cmd.title == cmd_spec["title"]
        assert cmd.tables == cmd_spec["tables"], cmd.ident
        assert cmd.permission.name == cmd_spec["permission"]


def test_legacy_register_command(monkeypatch):
    monkeypatch.setattr(cmk.gui.plugins.views.utils, "command_registry",
                        cmk.gui.plugins.views.utils.CommandRegistry())

    def render():
        pass

    def action():
        pass

    cmk.gui.plugins.views.utils.register_legacy_command({
        "tables": ["tabl"],
        "permission": "general.use",
        "title": "Bla Bla",
        "render": render,
        "action": action,
    })

    cmd = cmk.gui.plugins.views.utils.command_registry["blabla"]()
    assert isinstance(cmd, cmk.gui.plugins.views.utils.Command)
    assert cmd.ident == "blabla"
    assert cmd.title == "Bla Bla"
    assert cmd.permission == cmk.gui.default_permissions.PermissionGeneralUse


# These tests make adding new elements needlessly painful.
# Skip pending discussion with development team.
@pytest.mark.skip
def test_registered_datasources():
    expected: Dict[str, Dict[str, Any]] = {
        'alert_stats': {
            'add_columns': [
                'log_alerts_ok', 'log_alerts_warn', 'log_alerts_crit', 'log_alerts_unknown',
                'log_alerts_problem'
            ],
            'add_headers': 'Filter: class = 1\nStats: state = 0\nStats: state = 1\nStats: state = 2\nStats: state = 3\nStats: state != 0\n',
            'idkeys': ['host_name', 'service_description'],
            'ignore_limit': True,
            'infos': ['log', 'host', 'service', 'contact', 'command'],
            'keys': [],
            'table': 'log',
            'time_filters': ['logtime'],
            'title': u'Alert Statistics'
        },
        'bi_aggregations': {
            'idkeys': ['aggr_name'],
            'infos': ['aggr', 'aggr_group'],
            'keys': [],
            'table': ('func', 'table'),
            'title': u'BI Aggregations'
        },
        'bi_host_aggregations': {
            'idkeys': ['aggr_name'],
            'infos': ['aggr', 'host', 'aggr_group'],
            'keys': [],
            'table': ('func', 'host_table'),
            'title': u'BI Aggregations affected by one host'
        },
        'bi_hostname_aggregations': {
            'idkeys': ['aggr_name'],
            'infos': ['aggr', 'host', 'aggr_group'],
            'keys': [],
            'table': ('func', 'hostname_table'),
            'title': u'BI Hostname Aggregations'
        },
        'bi_hostnamebygroup_aggregations': {
            'idkeys': ['aggr_name'],
            'infos': ['aggr', 'host', 'hostgroup', 'aggr_group'],
            'keys': [],
            'table': ('func', 'hostname_by_group_table'),
            'title': u'BI Aggregations for Hosts by Hostgroups'
        },
        'comments': {
            'idkeys': ['comment_id'],
            'infos': ['comment', 'host', 'service'],
            'keys': ['comment_id', 'comment_type', 'host_name', 'service_description'],
            'table': 'comments',
            'title': u'Host- and Servicecomments'
        },
        'downtimes': {
            'idkeys': ['downtime_id'],
            'infos': ['downtime', 'host', 'service'],
            'keys': ['downtime_id', 'service_description'],
            'table': 'downtimes',
            'title': u'Scheduled Downtimes'
        },
        'hostgroups': {
            'idkeys': ['site', 'hostgroup_name'],
            'infos': ['hostgroup'],
            'keys': ['hostgroup_name'],
            'table': 'hostgroups',
            'title': u'Hostgroups'
        },
        'hosts': {
            'description': u'Displays a list of hosts.',
            'idkeys': ['site', 'host_name'],
            'infos': ['host'],
            'join': ('services', 'host_name'),
            'keys': ['host_name', 'host_downtimes'],
            'link_filters': {
                'hostgroup': 'opthostgroup'
            },
            'table': 'hosts',
            'title': u'All hosts'
        },
        'hostsbygroup': {
            'description': u'This datasource has a separate row for each group membership that a host has.',
            'idkeys': ['site', 'hostgroup_name', 'host_name'],
            'infos': ['host', 'hostgroup'],
            'join': ('services', 'host_name'),
            'keys': ['host_name', 'host_downtimes'],
            'table': 'hostsbygroup',
            'title': u'Hosts grouped by host groups'
        },
        'invbackplane': {
            'idkeys': [],
            'infos': ['host', 'invbackplane'],
            'keys': [],
            'table': ('func', 'inv_table'),
            'title': u'Inventory: Backplanes'
        },
        'invchassis': {
            'idkeys': [],
            'infos': ['host', 'invchassis'],
            'keys': [],
            'table': ('func', 'inv_table'),
            'title': u'Inventory: Chassis'
        },
        'invcontainer': {
            'idkeys': [],
            'infos': ['host', 'invcontainer'],
            'keys': [],
            'table': ('func', 'inv_table'),
            'title': u'Inventory: HW containers'
        },
        'invdockercontainers': {
            'idkeys': [],
            'infos': ['host', 'invdockercontainers'],
            'keys': [],
            'table': ('func', 'inv_table'),
            'title': u'Inventory: Docker containers'
        },
        'invdockerimages': {
            'idkeys': [],
            'infos': ['host', 'invdockerimages'],
            'keys': [],
            'table': ('func', 'inv_table'),
            'title': u'Inventory: Docker images'
        },
        'invfan': {
            'idkeys': [],
            'infos': ['host', 'invfan'],
            'keys': [],
            'table': ('func', 'inv_table'),
            'title': u'Inventory: Fans'
        },
        'invhist': {
            'idkeys': ['host_name', 'invhist_time'],
            'infos': ['host', 'invhist'],
            'keys': [],
            'table': ('func', 'inv_history_table'),
            'title': u'Inventory: History'
        },
        'invinterface': {
            'idkeys': [],
            'infos': ['host', 'invinterface'],
            'keys': [],
            'table': ('func', 'inv_table'),
            'title': u'Inventory: Network interfaces'
        },
        'invmodule': {
            'idkeys': [],
            'infos': ['host', 'invmodule'],
            'keys': [],
            'table': ('func', 'inv_table'),
            'title': u'Inventory: Modules'
        },
        'invoradataguardstats': {
            'idkeys': [],
            'infos': ['host', 'invoradataguardstats'],
            'keys': [],
            'table': ('func', 'inv_table'),
            'title': u'Inventory: Oracle dataguard statistics'
        },
        'invorainstance': {
            'idkeys': [],
            'infos': ['host', 'invorainstance'],
            'keys': [],
            'table': ('func', 'inv_table'),
            'title': u'Inventory: Oracle instances'
        },
        'invorarecoveryarea': {
            'idkeys': [],
            'infos': ['host', 'invorarecoveryarea'],
            'keys': [],
            'table': ('func', 'inv_table'),
            'title': u'Inventory: Oracle recovery areas'
        },
        'invorasga': {
            'idkeys': [],
            'infos': ['host', 'invorasga'],
            'keys': [],
            'table': ('func', 'inv_table'),
            'title': u'Inventory: Oracle performance'
        },
        'invoratablespace': {
            'idkeys': [],
            'infos': ['host', 'invoratablespace'],
            'keys': [],
            'table': ('func', 'inv_table'),
            'title': u'Inventory: Oracle tablespaces'
        },
        'invother': {
            'idkeys': [],
            'infos': ['host', 'invother'],
            'keys': [],
            'table': ('func', 'inv_table'),
            'title': u'Inventory: Other entities'
        },
        'invpsu': {
            'idkeys': [],
            'infos': ['host', 'invpsu'],
            'keys': [],
            'table': ('func', 'inv_table'),
            'title': u'Inventory: Power supplies'
        },
        'invsensor': {
            'idkeys': [],
            'infos': ['host', 'invsensor'],
            'keys': [],
            'table': ('func', 'inv_table'),
            'title': u'Inventory: Sensors'
        },
        'invstack': {
            'idkeys': [],
            'infos': ['host', 'invstack'],
            'keys': [],
            'table': ('func', 'inv_table'),
            'title': u'Inventory: Stacks'
        },
        'invswpac': {
            'idkeys': [],
            'infos': ['host', 'invswpac'],
            'keys': [],
            'table': ('func', 'inv_table'),
            'title': u'Inventory: Software packages'
        },
        'invunknown': {
            'idkeys': [],
            'infos': ['host', 'invunknown'],
            'keys': [],
            'table': ('func', 'inv_table'),
            'title': u'Inventory: Unknown entities'
        },
        'log': {
            'idkeys': ['log_lineno'],
            'infos': ['log', 'host', 'service', 'contact', 'command'],
            'keys': [],
            'table': 'log',
            'time_filters': ['logtime'],
            'title': u'The Logfile'
        },
        'log_events': {
            'add_headers': 'Filter: class = 1\nFilter: class = 3\nFilter: class = 8\nOr: 3\n',
            'idkeys': ['log_lineno'],
            'infos': ['log', 'host', 'service'],
            'keys': [],
            'table': 'log',
            'time_filters': ['logtime'],
            'title': u'Host and Service Events'
        },
        'log_host_events': {
            'add_headers': 'Filter: class = 1\nFilter: class = 3\nFilter: class = 8\nOr: 3\nFilter: service_description = \n',
            'idkeys': ['log_lineno'],
            'infos': ['log', 'host'],
            'keys': [],
            'table': 'log',
            'time_filters': ['logtime'],
            'title': u'Host Events'
        },
        'merged_hostgroups': {
            'idkeys': ['hostgroup_name'],
            'infos': ['hostgroup'],
            'keys': ['hostgroup_name'],
            'merge_by': 'hostgroup_name',
            'table': 'hostgroups',
            'title': u'Hostgroups, merged'
        },
        'merged_servicegroups': {
            'idkeys': ['servicegroup_name'],
            'infos': ['servicegroup'],
            'keys': ['servicegroup_name'],
            'merge_by': 'servicegroup_name',
            'table': 'servicegroups',
            'title': u'Servicegroups, merged'
        },
        'mkeventd_events': {
            'auth_domain': 'ec',
            'idkeys': ['site', 'host_name', 'event_id'],
            'infos': ['event', 'host'],
            'keys': [],
            'table': ('tuple', ('query_ec_table', ['eventconsoleevents'])),
            'time_filters': ['event_first'],
            'title': u'Event Console: Current Events'
        },
        'mkeventd_history': {
            'auth_domain': 'ec',
            'idkeys': ['site', 'host_name', 'event_id', 'history_line'],
            'infos': ['history', 'event', 'host'],
            'keys': [],
            'table': ('tuple', ('query_ec_table', ['eventconsolehistory'])),
            'time_filters': ['history_time'],
            'title': u'Event Console: Event History'
        },
        'service_discovery': {
            'add_columns': ['discovery_state', 'discovery_check', 'discovery_service'],
            'idkeys': ['host_name'],
            'infos': ['host', 'discovery'],
            'keys': [],
            'table': ('func', 'query_service_discovery'),
            'title': u'Service discovery'
        },
        'servicegroups': {
            'idkeys': ['site', 'servicegroup_name'],
            'infos': ['servicegroup'],
            'keys': ['servicegroup_name'],
            'table': 'servicegroups',
            'title': u'Servicegroups'
        },
        'services': {
            'idkeys': ['site', 'host_name', 'service_description'],
            'infos': ['service', 'host'],
            'joinkey': 'service_description',
            'keys': ['host_name', 'service_description', 'service_downtimes'],
            'link_filters': {
                'hostgroup': 'opthostgroup',
                'servicegroup': 'optservicegroup'
            },
            'table': 'services',
            'title': u'All services'
        },
        'servicesbygroup': {
            'idkeys': ['site', 'servicegroup_name', 'host_name', 'service_description'],
            'infos': ['service', 'host', 'servicegroup'],
            'keys': ['host_name', 'service_description', 'service_downtimes'],
            'table': 'servicesbygroup',
            'title': u'Services grouped by service groups'
        },
        'servicesbyhostgroup': {
            'idkeys': ['site', 'hostgroup_name', 'host_name', 'service_description'],
            'infos': ['service', 'host', 'hostgroup'],
            'keys': ['host_name', 'service_description', 'service_downtimes'],
            'table': 'servicesbyhostgroup',
            'title': u'Services grouped by host groups'
        },
    }

    names = cmk.gui.plugins.views.data_source_registry.keys()
    assert sorted(expected.keys()) == sorted(names)

    for ds_class in cmk.gui.plugins.views.utils.data_source_registry.values():
        ds = ds_class()
        spec = expected[ds.ident]
        assert ds.title == spec["title"]
        if hasattr(ds.table, '__call__'):
            # FIXME: ugly getattr so that mypy doesn't complain about missing attribute __name__
            name = getattr(ds.table, '__name__')
            assert ("func", name) == spec["table"]
        elif isinstance(ds.table, tuple):
            assert spec["table"][0] == "tuple"
            assert spec["table"][1][0] == ds.table[0].__name__
        else:
            assert ds.table == spec["table"]
        assert ds.keys == spec["keys"]
        assert ds.id_keys == spec["idkeys"]
        assert ds.infos == spec["infos"]


# These tests make adding new elements needlessly painful.
# Skip pending discussion with development team.
@pytest.mark.skip
def test_registered_painters():
    expected: Dict[str, Dict[str, Any]] = {
        'aggr_acknowledged': {
            'columns': ['aggr_effective_state'],
            'title': u'Acknowledged'
        },
        'aggr_assumed_state': {
            'columns': ['aggr_assumed_state'],
            'short': u'Assumed',
            'title': u'Aggregated assumed state'
        },
        'aggr_group': {
            'columns': ['aggr_group'],
            'short': u'Group',
            'title': u'Aggregation group'
        },
        'aggr_hosts': {
            'columns': ['aggr_hosts'],
            'short': u'Hosts',
            'title': u'Aggregation: affected hosts'
        },
        'aggr_hosts_services': {
            'columns': ['aggr_hosts'],
            'short': u'Hosts',
            'title': u'Aggregation: affected hosts (link to host page)'
        },
        'aggr_icons': {
            'columns': ['aggr_group', 'aggr_name', 'aggr_effective_state'],
            'printable': False,
            'title': u'Links'
        },
        'aggr_in_downtime': {
            'columns': ['aggr_effective_state'],
            'title': u'In Downtime'
        },
        'aggr_name': {
            'columns': ['aggr_name'],
            'short': u'Aggregation',
            'title': u'Aggregation name'
        },
        'aggr_output': {
            'columns': ['aggr_output'],
            'short': u'Output',
            'title': u'Aggregation status output'
        },
        'aggr_real_state': {
            'columns': ['aggr_state'],
            'short': u'R.State',
            'title': u'Aggregated real state (never assumed)'
        },
        'aggr_state': {
            'columns': ['aggr_effective_state'],
            'short': u'State',
            'title': u'Aggregated state'
        },
        'aggr_state_num': {
            'columns': ['aggr_effective_state'],
            'short': u'State',
            'title': u'Aggregated state (number)'
        },
        'aggr_treestate': {
            'columns': ['aggr_treestate', 'aggr_hosts'],
            'options': ['aggr_expand', 'aggr_onlyproblems', 'aggr_treetype', 'aggr_wrap'],
            'short': u'Tree',
            'title': u'Aggregation: complete tree'
        },
        'aggr_treestate_boxed': {
            'columns': ['aggr_treestate', 'aggr_hosts'],
            'short': u'Tree',
            'title': u'Aggregation: simplistic boxed layout'
        },
        'alert_stats_crit': {
            'columns': ['log_alerts_crit'],
            'short': u'CRIT',
            'title': u'Alert Statistics: Number of critical alerts'
        },
        'alert_stats_ok': {
            'columns': ['log_alerts_ok'],
            'short': u'OK',
            'title': u'Alert Statistics: Number of recoveries'
        },
        'alert_stats_problem': {
            'columns': ['log_alerts_problem'],
            'short': u'PROB',
            'title': u'Alert Statistics: Number of problem alerts'
        },
        'alert_stats_unknown': {
            'columns': ['log_alerts_unknown'],
            'short': u'UNKN',
            'title': u'Alert Statistics: Number of unknown alerts'
        },
        'alert_stats_warn': {
            'columns': ['log_alerts_warn'],
            'short': u'WARN',
            'title': u'Alert Statistics: Number of warnings'
        },
        'alias': {
            'columns': ['host_alias'],
            'short': u'Alias',
            'title': u'Host alias'
        },
        'check_manpage': {
            'columns': ['service_check_command'],
            'short': u'Manual',
            'title': u'Check manual (for Check_MK based checks)'
        },
        'comment_author': {
            'columns': ['comment_author'],
            'short': u'Author',
            'title': u'Comment author'
        },
        'comment_comment': {
            'columns': ['comment_comment'],
            'title': u'Comment text'
        },
        'comment_entry_type': {
            'columns': ['comment_entry_type', 'host_name', 'service_description'],
            'short': u'E.Type',
            'title': u'Comment entry type (user/downtime/flapping/ack)'
        },
        'comment_expires': {
            'columns': ['comment_expire_time'],
            'options': ['ts_format', 'ts_date'],
            'short': u'Expires',
            'title': u'Comment expiry time'
        },
        'comment_id': {
            'columns': ['comment_id'],
            'short': u'ID',
            'title': u'Comment id'
        },
        'comment_time': {
            'columns': ['comment_entry_time'],
            'options': ['ts_format', 'ts_date'],
            'short': u'Time',
            'title': u'Comment entry time'
        },
        'comment_what': {
            'columns': ['comment_type'],
            'short': u'Type',
            'title': u'Comment type (host/service)'
        },
        'deployment_downloaded_hash': {
            'columns': ['host_name'],
            'short': u'Downloaded Agent',
            'title': u'Agent Deployment: Downloaded Agent Hash'
        },
        'deployment_icons': {
            'columns': ['host_name'],
            'short': '',
            'title': u'Agent Deployment: Icons'
        },
        'deployment_installed_hash': {
            'columns': ['host_name'],
            'short': u'Installed Agent',
            'title': u'Agent Deployment: Installed Agent Hash'
        },
        'deployment_last_contact': {
            'columns': ['host_name'],
            'options': ['ts_format', 'ts_date'],
            'short': u'Last Contact',
            'title': u'Agent Deployment: Last Contact'
        },
        'deployment_last_download': {
            'columns': ['host_name'],
            'options': ['ts_format', 'ts_date'],
            'short': u'Last Download',
            'title': u'Agent Deployment: Last Download'
        },
        'deployment_last_error': {
            'columns': ['host_name'],
            'short': u'Last Error',
            'title': u'Agent Deployment: Last Error'
        },
        'deployment_target_hash': {
            'columns': ['host_name'],
            'short': u'Target Agent',
            'title': u'Agent Deployment: Target Agent Hash'
        },
        'downtime_author': {
            'columns': ['downtime_author'],
            'short': u'Author',
            'title': u'Downtime author'
        },
        'downtime_comment': {
            'columns': ['downtime_comment'],
            'short': u'Comment',
            'title': u'Downtime comment'
        },
        'downtime_duration': {
            'columns': ['downtime_duration', 'downtime_fixed'],
            'short': u'Flex. Duration',
            'title': u'Downtime duration (if flexible)'
        },
        'downtime_end_time': {
            'columns': ['downtime_end_time'],
            'options': ['ts_format', 'ts_date'],
            'short': u'End',
            'title': u'Downtime end time'
        },
        'downtime_entry_time': {
            'columns': ['downtime_entry_time'],
            'options': ['ts_format', 'ts_date'],
            'short': u'Entry',
            'title': u'Downtime entry time'
        },
        'downtime_fixed': {
            'columns': ['downtime_fixed'],
            'short': u'Mode',
            'title': u'Downtime start mode'
        },
        'downtime_id': {
            'columns': ['downtime_id'],
            'short': u'ID',
            'title': u'Downtime id'
        },
        'downtime_origin': {
            'columns': ['downtime_origin'],
            'short': u'Origin',
            'title': u'Downtime origin'
        },
        'downtime_recurring': {
            'columns': ['downtime_recurring'],
            'short': u'Recurring',
            'title': u'Downtime recurring interval'
        },
        'downtime_start_time': {
            'columns': ['downtime_start_time'],
            'options': ['ts_format', 'ts_date'],
            'short': u'Start',
            'title': u'Downtime start time'
        },
        'downtime_type': {
            'columns': ['downtime_type'],
            'short': u'act/pend',
            'title': u'Downtime active or pending'
        },
        'downtime_what': {
            'columns': ['downtime_is_service'],
            'short': u'for',
            'title': u'Downtime for host/service'
        },
        'event_application': {
            'columns': ['event_application'],
            'short': u'Application',
            'title': u'Application / Syslog-Tag'
        },
        'event_comment': {
            'columns': ['event_comment'],
            'short': u'Comment',
            'title': u'Comment to the event'
        },
        'event_contact': {
            'columns': ['event_contact'],
            'short': u'Contact',
            'title': u'Contact Person'
        },
        'event_contact_groups': {
            'columns': ['event_contact_groups'],
            'short': u'Rule contact groups',
            'title': u'Contact groups defined in rule'
        },
        'event_count': {
            'columns': ['event_count'],
            'short': u'Cnt.',
            'title': u'Count (number of recent occurrances)'
        },
        'event_effective_contact_groups': {
            'columns': [
                'event_contact_groups', 'event_contact_groups_precedence', 'host_contact_groups'
            ],
            'short': u'Contact groups',
            'title': u'Contact groups effective (Host or rule contact groups)'
        },
        'event_facility': {
            'columns': ['event_facility'],
            'short': u'Facility',
            'title': u'Syslog-Facility'
        },
        'event_first': {
            'columns': ['event_first'],
            'options': ['ts_format', 'ts_date'],
            'short': u'First',
            'title': u'Time of first occurrence of this serial'
        },
        'event_history_icons': {
            'columns': ['event_phase', 'event_host_in_downtime'],
            'printable': False,
            'short': u'Icons',
            'title': u'Event Icons'
        },
        'event_host': {
            'columns': ['event_host', 'host_name'],
            'short': u'Host',
            'title': u'Hostname'
        },
        'event_host_in_downtime': {
            'columns': ['event_host_in_downtime'],
            'short': u'Dt.',
            'title': u'Host in downtime during event creation'
        },
        'event_icons': {
            'columns': ['event_phase', 'event_host_in_downtime'],
            'printable': False,
            'short': u'Icons',
            'title': u'Event Icons'
        },
        'event_id': {
            'columns': ['event_id'],
            'short': u'ID',
            'title': u'ID of the event'
        },
        'event_ipaddress': {
            'columns': ['event_ipaddress'],
            'short': u'Orig. IP',
            'title': u'Original IP-Address'
        },
        'event_last': {
            'columns': ['event_last'],
            'options': ['ts_format', 'ts_date'],
            'short': u'Last',
            'title': u'Time of last occurrance'
        },
        'event_match_groups': {
            'columns': ['event_match_groups'],
            'short': u'Match',
            'title': u'Match Groups'
        },
        'event_owner': {
            'columns': ['event_owner'],
            'short': u'owner',
            'title': u'Owner of event'
        },
        'event_phase': {
            'columns': ['event_phase'],
            'short': u'Phase',
            'title': u'Phase of event (open, counting, etc.)'
        },
        'event_pid': {
            'columns': ['event_pid'],
            'short': u'PID',
            'title': u'Process ID'
        },
        'event_priority': {
            'columns': ['event_priority'],
            'short': u'Prio',
            'title': u'Syslog-Priority'
        },
        'event_rule_id': {
            'columns': ['event_rule_id'],
            'short': u'Rule',
            'title': u'Rule-ID'
        },
        'event_sl': {
            'columns': ['event_sl'],
            'short': u'Level',
            'title': u'Service-Level'
        },
        'event_state': {
            'columns': ['event_state'],
            'short': u'State',
            'title': u'State (severity) of event'
        },
        'event_text': {
            'columns': ['event_text'],
            'short': u'Message',
            'title': u'Text/Message of the event'
        },
        'hg_alias': {
            'columns': ['hostgroup_alias'],
            'short': u'Alias',
            'title': u'Hostgroup alias'
        },
        'hg_name': {
            'columns': ['hostgroup_name'],
            'short': u'Name',
            'title': u'Hostgroup name'
        },
        'hg_num_hosts_down': {
            'columns': ['hostgroup_num_hosts_down'],
            'short': u'Dw',
            'title': u'Number of hosts in state DOWN (Host Group)'
        },
        'hg_num_hosts_pending': {
            'columns': ['hostgroup_num_hosts_pending'],
            'short': u'Pd',
            'title': u'Number of hosts in state PENDING (Host Group)'
        },
        'hg_num_hosts_unreach': {
            'columns': ['hostgroup_num_hosts_unreach'],
            'short': u'Un',
            'title': u'Number of hosts in state UNREACH (Host Group)'
        },
        'hg_num_hosts_up': {
            'columns': ['hostgroup_num_hosts_up'],
            'short': u'Up',
            'title': u'Number of hosts in state UP (Host Group)'
        },
        'hg_num_services': {
            'columns': ['hostgroup_num_services'],
            'short': '',
            'title': u'Number of services (Host Group)'
        },
        'hg_num_services_crit': {
            'columns': ['hostgroup_num_services_crit'],
            'short': u'C',
            'title': u'Number of services in state CRIT (Host Group)'
        },
        'hg_num_services_ok': {
            'columns': ['hostgroup_num_services_ok'],
            'short': u'O',
            'title': u'Number of services in state OK (Host Group)'
        },
        'hg_num_services_pending': {
            'columns': ['hostgroup_num_services_pending'],
            'short': u'P',
            'title': u'Number of services in state PENDING (Host Group)'
        },
        'hg_num_services_unknown': {
            'columns': ['hostgroup_num_services_unknown'],
            'short': u'U',
            'title': u'Number of services in state UNKNOWN (Host Group)'
        },
        'hg_num_services_warn': {
            'columns': ['hostgroup_num_services_warn'],
            'short': u'W',
            'title': u'Number of services in state WARN (Host Group)'
        },
        'history_addinfo': {
            'columns': ['history_addinfo'],
            'short': u'Info',
            'title': u'Additional Information'
        },
        'history_line': {
            'columns': ['history_line'],
            'short': u'Line',
            'title': u'Line number in log file'
        },
        'history_time': {
            'columns': ['history_time'],
            'options': ['ts_format', 'ts_date'],
            'short': u'Time',
            'title': u'Time of entry in logfile'
        },
        'history_what': {
            'columns': ['history_what'],
            'short': u'Action',
            'title': u'Type of event action'
        },
        'history_what_explained': {
            'columns': ['history_what'],
            'title': u'Explanation for event action'
        },
        'history_who': {
            'columns': ['history_who'],
            'short': u'Who',
            'title': u'User who performed action'
        },
        'host': {
            'columns': [
                'host_name', 'host_state', 'host_has_been_checked', 'host_scheduled_downtime_depth'
            ],
            'short': u'Host',
            'sorter': 'site_host',
            'title': u'Hostname, with configurable colors'
        },
        'host_acknowledged': {
            'columns': ['host_acknowledged'],
            'short': u'Ack',
            'title': u'Host problem acknowledged'
        },
        'host_address': {
            'columns': ['host_address'],
            'short': u'IP address',
            'title': u'Host address (Primary)'
        },
        'host_address_families': {
            'columns': ['host_custom_variable_names', 'host_custom_variable_values'],
            'short': u'Address families',
            'title': u'Host address families'
        },
        'host_address_family': {
            'columns': ['host_custom_variable_names', 'host_custom_variable_values'],
            'short': u'Address family',
            'title': u'Host address family (Primary)'
        },
        'host_addresses': {
            'columns': [
                'host_address', 'host_custom_variable_names', 'host_custom_variable_values'
            ],
            'short': u'IP addresses',
            'title': u'Host addresses'
        },
        'host_attempt': {
            'columns': ['host_current_attempt', 'host_max_check_attempts'],
            'short': u'Att.',
            'title': u'Current host check attempt'
        },
        'host_black': {
            'columns': ['site', 'host_name', 'host_state'],
            'short': u'Host',
            'sorter': 'site_host',
            'title': u'Hostname, red background if down or unreachable (Deprecated)'
        },
        'host_black_nagios': {
            'columns': ['site', 'host_name', 'host_state'],
            'short': u'Host',
            'sorter': 'site_host',
            'title': u'Hostname, red background if down, link to Nagios services'
        },
        'host_check_age': {
            'columns': ['host_has_been_checked', 'host_last_check'],
            'options': ['ts_format', 'ts_date'],
            'short': u'Checked',
            'title': u'The time since the last check of the host'
        },
        'host_check_command': {
            'columns': ['host_check_command'],
            'short': u'Check command',
            'title': u'Host check command'
        },
        'host_check_command_expanded': {
            'columns': ['host_check_command_expanded'],
            'short': u'Check command expanded',
            'title': u'Host check command expanded'
        },
        'host_check_duration': {
            'columns': ['host_execution_time'],
            'short': u'Duration',
            'title': u'Host check duration'
        },
        'host_check_interval': {
            'columns': ['host_check_interval', 'host_retry_interval'],
            'short': u'Interval',
            'title': u'Normal/retry check interval'
        },
        'host_check_latency': {
            'columns': ['host_latency'],
            'short': u'Latency',
            'title': u'Host check latency'
        },
        'host_check_type': {
            'columns': ['host_check_type'],
            'short': u'Type',
            'title': u'Host check type'
        },
        'host_childs': {
            'columns': ['host_childs'],
            'short': u'children',
            'title': u"Host's children"
        },
        'host_comments': {
            'columns': ['host_comments_with_info'],
            'short': u'Comments',
            'title': u'Host comments'
        },
        'host_contact_groups': {
            'columns': ['host_contact_groups'],
            'short': u'Contact groups',
            'title': u'Host contact groups'
        },
        'host_contacts': {
            'columns': ['host_contacts'],
            'short': u'Contacts',
            'title': u'Host contacts'
        },
        'host_custom_notes': {
            'columns': ['host_name', 'host_address', 'host_plugin_output'],
            'short': u'Notes',
            'title': u'Custom host notes'
        },
        'host_custom_vars': {
            'columns': ['host_custom_variables'],
            'title': u'Host custom variables'
        },
        'host_filename': {
            'columns': ['host_filename'],
            'short': u'Filename',
            'title': u'Check_MK config filename'
        },
        'host_flapping': {
            'columns': ['host_is_flapping'],
            'short': u'Flap',
            'title': u'Host is flapping'
        },
        'host_graphs': {
            'columns': ['host_name', 'host_perf_data', 'host_metrics', 'host_check_command'],
            'options': ['pnp_timerange', 'graph_render_options'],
            'printable': 'time_graph',
            'title': u'Host Graphs with Timerange Previews'
        },
        'host_group_memberlist': {
            'columns': ['host_groups'],
            'short': u'Groups',
            'title': u'Host groups the host is member of'
        },
        'host_icons': {
            'columns': {
                'host_scheduled_downtime_depth',
                'host_in_check_period',
                'host_downtimes_with_extra_info',
                'site',
                'host_pnpgraph_present',
                'host_check_type',
                'host_accept_passive_checks',
                'host_icon_image',
                'host_is_flapping',
                'host_in_notification_period',
                'host_custom_variable_values',
                'host_modified_attributes_list',
                'host_filename',
                'host_acknowledged',
                'host_custom_variable_names',
                'host_action_url_expanded',
                'host_comments_with_extra_info',
                'host_in_service_period',
                'host_address',
                'host_staleness',
                'host_notifications_enabled',
                'host_active_checks_enabled',
                'host_perf_data',
                'host_check_command',
                'host_name',
                'host_notes_url_expanded',
            },
            'printable': False,
            'short': u'Icons',
            'title': u'Host icons'
        },
        'host_in_downtime': {
            'columns': ['host_scheduled_downtime_depth'],
            'short': u'Downtime',
            'title': u'Host in downtime'
        },
        'host_in_notifper': {
            'columns': ['host_in_notification_period'],
            'short': u'in notif. p.',
            'title': u'Host in notif. period'
        },
        'host_ipv4_address': {
            'columns': ['host_custom_variable_names', 'host_custom_variable_values'],
            'short': u'IPv4 address',
            'title': u'Host address (IPv4)'
        },
        'host_ipv6_address': {
            'columns': ['host_custom_variable_names', 'host_custom_variable_values'],
            'short': u'IPv6 address',
            'title': u'Host address (IPv6)'
        },
        'host_is_active': {
            'columns': ['host_active_checks_enabled'],
            'short': u'Active',
            'title': u'Host is active'
        },
        'host_is_stale': {
            'columns': ['host_staleness'],
            'short': u'Stale',
            'sorter': 'svc_staleness',
            'title': u'Host is stale'
        },
        'host_last_notification': {
            'columns': ['host_last_notification'],
            'options': ['ts_format', 'ts_date'],
            'short': u'last notification',
            'title': u'The time of the last host notification'
        },
        'host_nagios_link': {
            'columns': ['site', 'host_name'],
            'short': '',
            'title': u'Icon with link to host to Nagios GUI'
        },
        'host_next_check': {
            'columns': ['host_next_check'],
            'short': u'Next check',
            'title': u'The time of the next scheduled host check'
        },
        'host_next_notification': {
            'columns': ['host_next_notification'],
            'short': u'Next notification',
            'title': u'The time of the next host notification'
        },
        'host_normal_interval': {
            'columns': ['host_check_interval'],
            'short': u'Check int.',
            'title': u'Normal check interval'
        },
        'host_notification_number': {
            'columns': ['host_current_notification_number'],
            'short': u'N#',
            'title': u'Host notification number'
        },
        'host_notification_postponement_reason': {
            'columns': ['host_notification_postponement_reason'],
            'short': u'Notif. postponed',
            'title': u'Notification postponement reason'
        },
        'host_notifications_enabled': {
            'columns': ['host_notifications_enabled'],
            'short': u'Notif.',
            'title': u'Host notifications enabled'
        },
        'host_notifper': {
            'columns': ['host_notification_period'],
            'short': u'notif.',
            'title': u'Host notification period'
        },
        'host_parents': {
            'columns': ['host_parents'],
            'short': u'Parents',
            'title': u"Host's parents"
        },
        'host_perf_data': {
            'columns': ['host_perf_data'],
            'short': u'Performance data',
            'title': u'Host performance data'
        },
        'host_plugin_output': {
            'columns': ['host_plugin_output', 'host_custom_variables'],
            'short': u'Summary',
            'title': u'Summary'
        },
        'host_pnpgraph': {
            'columns': ['host_name', 'host_perf_data', 'host_metrics', 'host_check_command'],
            'options': ['pnp_timerange'],
            'printable': 'time_graph',
            'short': u'Graph',
            'title': u'Host graph'
        },
        'host_retry_interval': {
            'columns': ['host_retry_interval'],
            'short': u'Retry',
            'title': u'Retry check interval'
        },
        'host_servicelevel': {
            'columns': ['host_custom_variable_names', 'host_custom_variable_values'],
            'short': u'Service Level',
            'sorter': 'servicelevel',
            'title': u'Host service level'
        },
        'host_services': {
            'columns': ['host_name', 'host_services_with_state'],
            'short': u'Services',
            'title': u'Services colored according to state'
        },
        'host_staleness': {
            'columns': ['host_staleness'],
            'short': u'Staleness',
            'title': u'Host staleness value'
        },
        'host_state': {
            'columns': ['host_has_been_checked', 'host_state'],
            'short': u'state',
            'sorter': 'hoststate',
            'title': u'Host state'
        },
        'host_state_age': {
            'columns': ['host_has_been_checked', 'host_last_state_change'],
            'options': ['ts_format', 'ts_date'],
            'short': u'Age',
            'title': u'The age of the current host state'
        },
        'host_state_onechar': {
            'columns': ['host_has_been_checked', 'host_state'],
            'short': u'S.',
            'sorter': 'hoststate',
            'title': u'Host state (first character)'
        },
        'host_tag_address_family': {
            "title": "Host tag: Address / IP Address Family ",
            "short": "IP Address Family ",
            "columns": ["host_custom_variables"],
        },
        'host_tag_agent': {
            "title": "Host tag: Data sources / Check_MK Agent",
            "short": "Check_MK Agent",
            "columns": ["host_custom_variables"],
        },
        'host_tag_snmp': {
            "title": "Host tag: Data sources / SNMP",
            "short": "SNMP",
            "columns": ["host_custom_variables"],
        },
        'host_tags': {
            'columns': ['host_custom_variable_names', 'host_custom_variable_values'],
            'short': u'Tags',
            'sorter': 'host',
            'title': u'Host tags (raw)'
        },
        'host_tags_with_titles': {
            'columns': ['host_custom_variable_names', 'host_custom_variable_values'],
            'short': u'Tags',
            'sorter': 'host',
            'title': u'Host tags (with titles)'
        },
        'host_with_state': {
            'columns': ['site', 'host_name', 'host_state', 'host_has_been_checked'],
            'short': u'Host',
            'sorter': 'site_host',
            'title': u'Hostname, marked red if down (Deprecated)'
        },
        'hostgroup_hosts': {
            'columns': ['hostgroup_members_with_state'],
            'short': u'Hosts',
            'title': u'Hosts colored according to state (Host Group)'
        },
        'invbackplane_description': {
            'columns': ['invbackplane_description'],
            'short': u'Description',
            'sorter': 'invbackplane_description',
            'title': u'Backplane: Description'
        },
        'invbackplane_index': {
            'columns': ['invbackplane_index'],
            'short': u'Index',
            'sorter': 'invbackplane_index',
            'title': u'Backplane: Index'
        },
        'invbackplane_location': {
            'columns': ['invbackplane_location'],
            'short': u'Location',
            'sorter': 'invbackplane_location',
            'title': u'Backplane: Location'
        },
        'invbackplane_manufacturer': {
            'columns': ['invbackplane_manufacturer'],
            'short': u'Manufacturer',
            'sorter': 'invbackplane_manufacturer',
            'title': u'Backplane: Manufacturer'
        },
        'invbackplane_model': {
            'columns': ['invbackplane_model'],
            'short': u'Model Name',
            'sorter': 'invbackplane_model',
            'title': u'Backplane: Model Name'
        },
        'invbackplane_name': {
            'columns': ['invbackplane_name'],
            'short': u'Name',
            'sorter': 'invbackplane_name',
            'title': u'Backplane: Name'
        },
        'invbackplane_serial': {
            'columns': ['invbackplane_serial'],
            'short': u'Serial Number',
            'sorter': 'invbackplane_serial',
            'title': u'Backplane: Serial Number'
        },
        'invbackplane_software': {
            'columns': ['invbackplane_software'],
            'short': u'Software',
            'sorter': 'invbackplane_software',
            'title': u'Backplane: Software'
        },
        'invchassis_description': {
            'columns': ['invchassis_description'],
            'short': u'Description',
            'sorter': 'invchassis_description',
            'title': u'Chassis: Description'
        },
        'invchassis_index': {
            'columns': ['invchassis_index'],
            'short': u'Index',
            'sorter': 'invchassis_index',
            'title': u'Chassis: Index'
        },
        'invchassis_location': {
            'columns': ['invchassis_location'],
            'short': u'Location',
            'sorter': 'invchassis_location',
            'title': u'Chassis: Location'
        },
        'invchassis_manufacturer': {
            'columns': ['invchassis_manufacturer'],
            'short': u'Manufacturer',
            'sorter': 'invchassis_manufacturer',
            'title': u'Chassis: Manufacturer'
        },
        'invchassis_model': {
            'columns': ['invchassis_model'],
            'short': u'Model Name',
            'sorter': 'invchassis_model',
            'title': u'Chassis: Model Name'
        },
        'invchassis_name': {
            'columns': ['invchassis_name'],
            'short': u'Name',
            'sorter': 'invchassis_name',
            'title': u'Chassis: Name'
        },
        'invchassis_serial': {
            'columns': ['invchassis_serial'],
            'short': u'Serial Number',
            'sorter': 'invchassis_serial',
            'title': u'Chassis: Serial Number'
        },
        'invchassis_software': {
            'columns': ['invchassis_software'],
            'short': u'Software',
            'sorter': 'invchassis_software',
            'title': u'Chassis: Software'
        },
        'invcontainer_description': {
            'columns': ['invcontainer_description'],
            'short': u'Description',
            'sorter': 'invcontainer_description',
            'title': u'HW container: Description'
        },
        'invcontainer_index': {
            'columns': ['invcontainer_index'],
            'short': u'Index',
            'sorter': 'invcontainer_index',
            'title': u'HW container: Index'
        },
        'invcontainer_location': {
            'columns': ['invcontainer_location'],
            'short': u'Location',
            'sorter': 'invcontainer_location',
            'title': u'HW container: Location'
        },
        'invcontainer_manufacturer': {
            'columns': ['invcontainer_manufacturer'],
            'short': u'Manufacturer',
            'sorter': 'invcontainer_manufacturer',
            'title': u'HW container: Manufacturer'
        },
        'invcontainer_model': {
            'columns': ['invcontainer_model'],
            'short': u'Model Name',
            'sorter': 'invcontainer_model',
            'title': u'HW container: Model Name'
        },
        'invcontainer_name': {
            'columns': ['invcontainer_name'],
            'short': u'Name',
            'sorter': 'invcontainer_name',
            'title': u'HW container: Name'
        },
        'invcontainer_serial': {
            'columns': ['invcontainer_serial'],
            'short': u'Serial Number',
            'sorter': 'invcontainer_serial',
            'title': u'HW container: Serial Number'
        },
        'invcontainer_software': {
            'columns': ['invcontainer_software'],
            'short': u'Software',
            'sorter': 'invcontainer_software',
            'title': u'HW container: Software'
        },
        'invdockercontainers_creation': {
            'columns': ['invdockercontainers_creation'],
            'short': 'Creation',
            'sorter': 'invdockercontainers_creation',
            'title': u'Docker containers: Creation'
        },
        'invdockercontainers_id': {
            'columns': ['invdockercontainers_id'],
            'short': u'ID',
            'sorter': 'invdockercontainers_id',
            'title': u'Docker containers: ID'
        },
        'invdockercontainers_labels': {
            'columns': ['invdockercontainers_labels'],
            'short': 'Labels',
            'sorter': 'invdockercontainers_labels',
            'title': u'Docker containers: Labels'
        },
        'invdockercontainers_name': {
            'columns': ['invdockercontainers_name'],
            'short': 'Name',
            'sorter': 'invdockercontainers_name',
            'title': u'Docker containers: Name'
        },
        'invdockercontainers_repository': {
            'columns': ['invdockercontainers_repository'],
            'short': 'Repository',
            'sorter': 'invdockercontainers_repository',
            'title': u'Docker containers: Repository'
        },
        'invdockercontainers_status': {
            'columns': ['invdockercontainers_status'],
            'short': 'Status',
            'sorter': 'invdockercontainers_status',
            'title': u'Docker containers: Status'
        },
        'invdockercontainers_tag': {
            'columns': ['invdockercontainers_tag'],
            'short': 'Tag',
            'sorter': 'invdockercontainers_tag',
            'title': u'Docker containers: Tag'
        },
        'invdockerimages_amount_containers': {
            'columns': ['invdockerimages_amount_containers'],
            'short': u'# Containers',
            'sorter': 'invdockerimages_amount_containers',
            'title': u'Docker images: # Containers'
        },
        'invdockerimages_creation': {
            'columns': ['invdockerimages_creation'],
            'short': 'Creation',
            'sorter': 'invdockerimages_creation',
            'title': u'Docker images: Creation'
        },
        'invdockerimages_id': {
            'columns': ['invdockerimages_id'],
            'short': u'ID',
            'sorter': 'invdockerimages_id',
            'title': u'Docker images: ID'
        },
        'invdockerimages_labels': {
            'columns': ['invdockerimages_labels'],
            'short': 'Labels',
            'sorter': 'invdockerimages_labels',
            'title': u'Docker images: Labels'
        },
        'invdockerimages_repository': {
            'columns': ['invdockerimages_repository'],
            'short': 'Repository',
            'sorter': 'invdockerimages_repository',
            'title': u'Docker images: Repository'
        },
        'invdockerimages_size': {
            'columns': ['invdockerimages_size'],
            'short': 'Size',
            'sorter': 'invdockerimages_size',
            'title': u'Docker images: Size'
        },
        'invdockerimages_tag': {
            'columns': ['invdockerimages_tag'],
            'short': 'Tag',
            'sorter': 'invdockerimages_tag',
            'title': u'Docker images: Tag'
        },
        'inventory_tree': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'options': ['show_internal_tree_paths'],
            'title': u'Hardware & Software Tree'
        },
        'invfan_description': {
            'columns': ['invfan_description'],
            'short': u'Description',
            'sorter': 'invfan_description',
            'title': u'Fan: Description'
        },
        'invfan_index': {
            'columns': ['invfan_index'],
            'short': u'Index',
            'sorter': 'invfan_index',
            'title': u'Fan: Index'
        },
        'invfan_location': {
            'columns': ['invfan_location'],
            'short': u'Location',
            'sorter': 'invfan_location',
            'title': u'Fan: Location'
        },
        'invfan_manufacturer': {
            'columns': ['invfan_manufacturer'],
            'short': u'Manufacturer',
            'sorter': 'invfan_manufacturer',
            'title': u'Fan: Manufacturer'
        },
        'invfan_model': {
            'columns': ['invfan_model'],
            'short': u'Model Name',
            'sorter': 'invfan_model',
            'title': u'Fan: Model Name'
        },
        'invfan_name': {
            'columns': ['invfan_name'],
            'short': u'Name',
            'sorter': 'invfan_name',
            'title': u'Fan: Name'
        },
        'invfan_serial': {
            'columns': ['invfan_serial'],
            'short': u'Serial Number',
            'sorter': 'invfan_serial',
            'title': u'Fan: Serial Number'
        },
        'invfan_software': {
            'columns': ['invfan_software'],
            'short': u'Software',
            'sorter': 'invfan_software',
            'title': u'Fan: Software'
        },
        'invhist_changed': {
            'columns': ['invhist_changed'],
            'short': u'changed',
            'title': u'changed entries'
        },
        'invhist_delta': {
            'columns': ['invhist_deltainvhist_time'],
            'title': u'Inventory changes'
        },
        'invhist_new': {
            'columns': ['invhist_new'],
            'short': u'new',
            'title': u'new entries'
        },
        'invhist_removed': {
            'columns': ['invhist_removed'],
            'short': u'Removed',
            'title': u'Removed entries'
        },
        'invhist_time': {
            'columns': ['invhist_time'],
            'options': ['ts_format', 'ts_date'],
            'short': u'Date/Time',
            'title': u'Inventory Date/Time'
        },
        'invinterface_admin_status': {
            'columns': ['invinterface_admin_status'],
            'short': u'Admin',
            'sorter': 'invinterface_admin_status',
            'title': u'Network interface: Administrative Status'
        },
        'invinterface_alias': {
            'columns': ['invinterface_alias'],
            'short': u'Alias',
            'sorter': 'invinterface_alias',
            'title': u'Network interface: Alias'
        },
        'invinterface_available': {
            'columns': ['invinterface_available'],
            'short': u'Used',
            'sorter': 'invinterface_available',
            'title': u'Network interface: Port Usage'
        },
        'invinterface_description': {
            'columns': ['invinterface_description'],
            'short': u'Description',
            'sorter': 'invinterface_description',
            'title': u'Network interface: Description'
        },
        'invinterface_index': {
            'columns': ['invinterface_index'],
            'short': u'Index',
            'sorter': 'invinterface_index',
            'title': u'Network interface: Index'
        },
        'invinterface_last_change': {
            'columns': ['invinterface_last_change'],
            'short': u'Last Change',
            'sorter': 'invinterface_last_change',
            'title': u'Network interface: Last Change'
        },
        'invinterface_oper_status': {
            'columns': ['invinterface_oper_status'],
            'short': u'Status',
            'sorter': 'invinterface_oper_status',
            'title': u'Network interface: Operational Status'
        },
        'invinterface_phys_address': {
            'columns': ['invinterface_phys_address'],
            'short': u'Physical Address (MAC)',
            'sorter': 'invinterface_phys_address',
            'title': u'Network interface: Physical Address (MAC)'
        },
        'invinterface_port_type': {
            'columns': ['invinterface_port_type'],
            'short': u'Type',
            'sorter': 'invinterface_port_type',
            'title': u'Network interface: Type'
        },
        'invinterface_speed': {
            'columns': ['invinterface_speed'],
            'short': u'Speed',
            'sorter': 'invinterface_speed',
            'title': u'Network interface: Speed'
        },
        'invinterface_vlans': {
            'columns': ['invinterface_vlans'],
            'short': u'VLANs',
            'sorter': 'invinterface_vlans',
            'title': u'Network interface: VLANs'
        },
        'invinterface_vlantype': {
            'columns': ['invinterface_vlantype'],
            'short': u'VLAN type',
            'sorter': 'invinterface_vlantype',
            'title': u'Network interface: VLAN type'
        },
        'invmodule_bootloader': {
            'columns': ['invmodule_bootloader'],
            'short': u'Bootloader',
            'sorter': 'invmodule_bootloader',
            'title': u'Module: Bootloader'
        },
        'invmodule_description': {
            'columns': ['invmodule_description'],
            'short': u'Description',
            'sorter': 'invmodule_description',
            'title': u'Module: Description'
        },
        'invmodule_firmware': {
            'columns': ['invmodule_firmware'],
            'short': u'Firmware',
            'sorter': 'invmodule_firmware',
            'title': u'Module: Firmware'
        },
        'invmodule_index': {
            'columns': ['invmodule_index'],
            'short': u'Index',
            'sorter': 'invmodule_index',
            'title': u'Module: Index'
        },
        'invmodule_location': {
            'columns': ['invmodule_location'],
            'short': u'Location',
            'sorter': 'invmodule_location',
            'title': u'Module: Location'
        },
        'invmodule_manufacturer': {
            'columns': ['invmodule_manufacturer'],
            'short': u'Manufacturer',
            'sorter': 'invmodule_manufacturer',
            'title': u'Module: Manufacturer'
        },
        'invmodule_model': {
            'columns': ['invmodule_model'],
            'short': u'Model Name',
            'sorter': 'invmodule_model',
            'title': u'Module: Model Name'
        },
        'invmodule_name': {
            'columns': ['invmodule_name'],
            'short': u'Name',
            'sorter': 'invmodule_name',
            'title': u'Module: Name'
        },
        'invmodule_serial': {
            'columns': ['invmodule_serial'],
            'short': u'Serial Number',
            'sorter': 'invmodule_serial',
            'title': u'Module: Serial Number'
        },
        'invmodule_software': {
            'columns': ['invmodule_software'],
            'short': u'Software',
            'sorter': 'invmodule_software',
            'title': u'Module: Software'
        },
        'invmodule_type': {
            'columns': ['invmodule_type'],
            'short': u'Type',
            'sorter': 'invmodule_type',
            'title': u'Module: Type'
        },
        'invoradataguardstats_db_unique': {
            'columns': ['invoradataguardstats_db_unique'],
            'short': u'Name',
            'sorter': 'invoradataguardstats_db_unique',
            'title': u'Oracle dataguard statistic: Name'
        },
        'invoradataguardstats_role': {
            'columns': ['invoradataguardstats_role'],
            'short': u'Role',
            'sorter': 'invoradataguardstats_role',
            'title': u'Oracle dataguard statistic: Role'
        },
        'invoradataguardstats_sid': {
            'columns': ['invoradataguardstats_sid'],
            'short': u'SID',
            'sorter': 'invoradataguardstats_sid',
            'title': u'Oracle dataguard statistic: SID'
        },
        'invoradataguardstats_switchover': {
            'columns': ['invoradataguardstats_switchover'],
            'short': u'Switchover',
            'sorter': 'invoradataguardstats_switchover',
            'title': u'Oracle dataguard statistic: Switchover'
        },
        'invorainstance_db_creation_time': {
            'columns': ['invorainstance_db_creation_time'],
            'short': u'Creation time',
            'sorter': 'invorainstance_db_creation_time',
            'title': u'Oracle instance: Creation time'
        },
        'invorainstance_db_uptime': {
            'columns': ['invorainstance_db_uptime'],
            'short': u'Uptime',
            'sorter': 'invorainstance_db_uptime',
            'title': u'Oracle instance: Uptime'
        },
        'invorainstance_logins': {
            'columns': ['invorainstance_logins'],
            'short': u'Logins',
            'sorter': 'invorainstance_logins',
            'title': u'Oracle instance: Logins'
        },
        'invorainstance_logmode': {
            'columns': ['invorainstance_logmode'],
            'short': u'Log mode',
            'sorter': 'invorainstance_logmode',
            'title': u'Oracle instance: Log mode'
        },
        'invorainstance_openmode': {
            'columns': ['invorainstance_openmode'],
            'short': u'Open mode',
            'sorter': 'invorainstance_openmode',
            'title': u'Oracle instance: Open mode'
        },
        'invorainstance_sid': {
            'columns': ['invorainstance_sid'],
            'short': u'SID',
            'sorter': 'invorainstance_sid',
            'title': u'Oracle instance: SID'
        },
        'invorainstance_version': {
            'columns': ['invorainstance_version'],
            'short': u'Version',
            'sorter': 'invorainstance_version',
            'title': u'Oracle instance: Version'
        },
        'invorarecoveryarea_flashback': {
            'columns': ['invorarecoveryarea_flashback'],
            'short': u'Flashback',
            'sorter': 'invorarecoveryarea_flashback',
            'title': u'Oracle recovery area: Flashback'
        },
        'invorarecoveryarea_sid': {
            'columns': ['invorarecoveryarea_sid'],
            'short': u'SID',
            'sorter': 'invorarecoveryarea_sid',
            'title': u'Oracle recovery area: SID'
        },
        'invorasga_buf_cache_size': {
            'columns': ['invorasga_buf_cache_size'],
            'short': u'Buffer cache size',
            'sorter': 'invorasga_buf_cache_size',
            'title': u'Oracle performance: Buffer cache size'
        },
        'invorasga_data_trans_cache_size': {
            'columns': ['invorasga_data_trans_cache_size'],
            'short': u'Data transfer cache size',
            'sorter': 'invorasga_data_trans_cache_size',
            'title': u'Oracle performance: Data transfer cache size'
        },
        'invorasga_fixed_size': {
            'columns': ['invorasga_fixed_size'],
            'short': u'Fixed size',
            'sorter': 'invorasga_fixed_size',
            'title': u'Oracle performance: Fixed size'
        },
        'invorasga_free_mem_avail': {
            'columns': ['invorasga_free_mem_avail'],
            'short': u'Free SGA memory available',
            'sorter': 'invorasga_free_mem_avail',
            'title': u'Oracle performance: Free SGA memory available'
        },
        'invorasga_granule_size': {
            'columns': ['invorasga_granule_size'],
            'short': u'Granule size',
            'sorter': 'invorasga_granule_size',
            'title': u'Oracle performance: Granule size'
        },
        'invorasga_in_mem_area_size': {
            'columns': ['invorasga_in_mem_area_size'],
            'short': u'In-memory area',
            'sorter': 'invorasga_in_mem_area_size',
            'title': u'Oracle performance: In-memory area'
        },
        'invorasga_java_pool_size': {
            'columns': ['invorasga_java_pool_size'],
            'short': u'Java pool size',
            'sorter': 'invorasga_java_pool_size',
            'title': u'Oracle performance: Java pool size'
        },
        'invorasga_large_pool_size': {
            'columns': ['invorasga_large_pool_size'],
            'short': u'Large pool size',
            'sorter': 'invorasga_large_pool_size',
            'title': u'Oracle performance: Large pool size'
        },
        'invorasga_max_size': {
            'columns': ['invorasga_max_size'],
            'short': u'Maximum size',
            'sorter': 'invorasga_max_size',
            'title': u'Oracle performance: Maximum size'
        },
        'invorasga_redo_buffer': {
            'columns': ['invorasga_redo_buffer'],
            'short': u'Redo buffers',
            'sorter': 'invorasga_redo_buffer',
            'title': u'Oracle performance: Redo buffers'
        },
        'invorasga_shared_io_pool_size': {
            'columns': ['invorasga_shared_io_pool_size'],
            'short': u'Shared pool size',
            'sorter': 'invorasga_shared_io_pool_size',
            'title': u'Oracle performance: Shared pool size'
        },
        'invorasga_shared_pool_size': {
            'columns': ['invorasga_shared_pool_size'],
            'short': u'Shared pool size',
            'sorter': 'invorasga_shared_pool_size',
            'title': u'Oracle performance: Shared pool size'
        },
        'invorasga_sid': {
            'columns': ['invorasga_sid'],
            'short': u'SID',
            'sorter': 'invorasga_sid',
            'title': u'Oracle performance: SID'
        },
        'invorasga_start_oh_shared_pool': {
            'columns': ['invorasga_start_oh_shared_pool'],
            'short': u'Startup overhead in shared pool',
            'sorter': 'invorasga_start_oh_shared_pool',
            'title': u'Oracle performance: Startup overhead in shared pool'
        },
        'invorasga_streams_pool_size': {
            'columns': ['invorasga_streams_pool_size'],
            'short': u'Streams pool size',
            'sorter': 'invorasga_streams_pool_size',
            'title': u'Oracle performance: Streams pool size'
        },
        'invoratablespace_autoextensible': {
            'columns': ['invoratablespace_autoextensible'],
            'short': u'Autoextensible',
            'sorter': 'invoratablespace_autoextensible',
            'title': u'Oracle tablespace: Autoextensible'
        },
        'invoratablespace_current_size': {
            'columns': ['invoratablespace_current_size'],
            'short': u'Current size',
            'sorter': 'invoratablespace_current_size',
            'title': u'Oracle tablespace: Current size'
        },
        'invoratablespace_free_space': {
            'columns': ['invoratablespace_free_space'],
            'short': u'Free space',
            'sorter': 'invoratablespace_free_space',
            'title': u'Oracle tablespace: Free space'
        },
        'invoratablespace_increment_size': {
            'columns': ['invoratablespace_increment_size'],
            'short': u'Increment size',
            'sorter': 'invoratablespace_increment_size',
            'title': u'Oracle tablespace: Increment size'
        },
        'invoratablespace_max_size': {
            'columns': ['invoratablespace_max_size'],
            'short': u'Max. size',
            'sorter': 'invoratablespace_max_size',
            'title': u'Oracle tablespace: Max. size'
        },
        'invoratablespace_name': {
            'columns': ['invoratablespace_name'],
            'short': u'Name',
            'sorter': 'invoratablespace_name',
            'title': u'Oracle tablespace: Name'
        },
        'invoratablespace_num_increments': {
            'columns': ['invoratablespace_num_increments'],
            'short': u'Number of increments',
            'sorter': 'invoratablespace_num_increments',
            'title': u'Oracle tablespace: Number of increments'
        },
        'invoratablespace_sid': {
            'columns': ['invoratablespace_sid'],
            'short': u'SID',
            'sorter': 'invoratablespace_sid',
            'title': u'Oracle tablespace: SID'
        },
        'invoratablespace_type': {
            'columns': ['invoratablespace_type'],
            'short': u'Type',
            'sorter': 'invoratablespace_type',
            'title': u'Oracle tablespace: Type'
        },
        'invoratablespace_used_size': {
            'columns': ['invoratablespace_used_size'],
            'short': u'Used size',
            'sorter': 'invoratablespace_used_size',
            'title': u'Oracle tablespace: Used size'
        },
        'invoratablespace_version': {
            'columns': ['invoratablespace_version'],
            'short': u'Version',
            'sorter': 'invoratablespace_version',
            'title': u'Oracle tablespace: Version'
        },
        'invother_description': {
            'columns': ['invother_description'],
            'short': u'Description',
            'sorter': 'invother_description',
            'title': u'Other entity: Description'
        },
        'invother_index': {
            'columns': ['invother_index'],
            'short': u'Index',
            'sorter': 'invother_index',
            'title': u'Other entity: Index'
        },
        'invother_location': {
            'columns': ['invother_location'],
            'short': u'Location',
            'sorter': 'invother_location',
            'title': u'Other entity: Location'
        },
        'invother_manufacturer': {
            'columns': ['invother_manufacturer'],
            'short': u'Manufacturer',
            'sorter': 'invother_manufacturer',
            'title': u'Other entity: Manufacturer'
        },
        'invother_model': {
            'columns': ['invother_model'],
            'short': u'Model Name',
            'sorter': 'invother_model',
            'title': u'Other entity: Model Name'
        },
        'invother_name': {
            'columns': ['invother_name'],
            'short': u'Name',
            'sorter': 'invother_name',
            'title': u'Other entity: Name'
        },
        'invother_serial': {
            'columns': ['invother_serial'],
            'short': u'Serial Number',
            'sorter': 'invother_serial',
            'title': u'Other entity: Serial Number'
        },
        'invother_software': {
            'columns': ['invother_software'],
            'short': u'Software',
            'sorter': 'invother_software',
            'title': u'Other entity: Software'
        },
        'invpsu_description': {
            'columns': ['invpsu_description'],
            'short': u'Description',
            'sorter': 'invpsu_description',
            'title': u'Power supply: Description'
        },
        'invpsu_index': {
            'columns': ['invpsu_index'],
            'short': u'Index',
            'sorter': 'invpsu_index',
            'title': u'Power supply: Index'
        },
        'invpsu_location': {
            'columns': ['invpsu_location'],
            'short': u'Location',
            'sorter': 'invpsu_location',
            'title': u'Power supply: Location'
        },
        'invpsu_manufacturer': {
            'columns': ['invpsu_manufacturer'],
            'short': u'Manufacturer',
            'sorter': 'invpsu_manufacturer',
            'title': u'Power supply: Manufacturer'
        },
        'invpsu_model': {
            'columns': ['invpsu_model'],
            'short': u'Model Name',
            'sorter': 'invpsu_model',
            'title': u'Power supply: Model Name'
        },
        'invpsu_name': {
            'columns': ['invpsu_name'],
            'short': u'Name',
            'sorter': 'invpsu_name',
            'title': u'Power supply: Name'
        },
        'invpsu_serial': {
            'columns': ['invpsu_serial'],
            'short': u'Serial Number',
            'sorter': 'invpsu_serial',
            'title': u'Power supply: Serial Number'
        },
        'invpsu_software': {
            'columns': ['invpsu_software'],
            'short': u'Software',
            'sorter': 'invpsu_software',
            'title': u'Power supply: Software'
        },
        'invsensor_description': {
            'columns': ['invsensor_description'],
            'short': u'Description',
            'sorter': 'invsensor_description',
            'title': u'Sensor: Description'
        },
        'invsensor_index': {
            'columns': ['invsensor_index'],
            'short': u'Index',
            'sorter': 'invsensor_index',
            'title': u'Sensor: Index'
        },
        'invsensor_location': {
            'columns': ['invsensor_location'],
            'short': u'Location',
            'sorter': 'invsensor_location',
            'title': u'Sensor: Location'
        },
        'invsensor_manufacturer': {
            'columns': ['invsensor_manufacturer'],
            'short': u'Manufacturer',
            'sorter': 'invsensor_manufacturer',
            'title': u'Sensor: Manufacturer'
        },
        'invsensor_model': {
            'columns': ['invsensor_model'],
            'short': u'Model Name',
            'sorter': 'invsensor_model',
            'title': u'Sensor: Model Name'
        },
        'invsensor_name': {
            'columns': ['invsensor_name'],
            'short': u'Name',
            'sorter': 'invsensor_name',
            'title': u'Sensor: Name'
        },
        'invsensor_serial': {
            'columns': ['invsensor_serial'],
            'short': u'Serial Number',
            'sorter': 'invsensor_serial',
            'title': u'Sensor: Serial Number'
        },
        'invsensor_software': {
            'columns': ['invsensor_software'],
            'short': u'Software',
            'sorter': 'invsensor_software',
            'title': u'Sensor: Software'
        },
        'invstack_description': {
            'columns': ['invstack_description'],
            'short': u'Description',
            'sorter': 'invstack_description',
            'title': u'Stack: Description'
        },
        'invstack_index': {
            'columns': ['invstack_index'],
            'short': u'Index',
            'sorter': 'invstack_index',
            'title': u'Stack: Index'
        },
        'invstack_location': {
            'columns': ['invstack_location'],
            'short': u'Location',
            'sorter': 'invstack_location',
            'title': u'Stack: Location'
        },
        'invstack_manufacturer': {
            'columns': ['invstack_manufacturer'],
            'short': u'Manufacturer',
            'sorter': 'invstack_manufacturer',
            'title': u'Stack: Manufacturer'
        },
        'invstack_model': {
            'columns': ['invstack_model'],
            'short': u'Model Name',
            'sorter': 'invstack_model',
            'title': u'Stack: Model Name'
        },
        'invstack_name': {
            'columns': ['invstack_name'],
            'short': u'Name',
            'sorter': 'invstack_name',
            'title': u'Stack: Name'
        },
        'invstack_serial': {
            'columns': ['invstack_serial'],
            'short': u'Serial Number',
            'sorter': 'invstack_serial',
            'title': u'Stack: Serial Number'
        },
        'invstack_software': {
            'columns': ['invstack_software'],
            'short': u'Software',
            'sorter': 'invstack_software',
            'title': u'Stack: Software'
        },
        'invswpac_arch': {
            'columns': ['invswpac_arch'],
            'short': u'Architecture',
            'sorter': 'invswpac_arch',
            'title': u'Software package: Architecture'
        },
        'invswpac_install_date': {
            'columns': ['invswpac_install_date'],
            'short': u'Install Date',
            'sorter': 'invswpac_install_date',
            'title': u'Software package: Install Date'
        },
        'invswpac_name': {
            'columns': ['invswpac_name'],
            'short': u'Name',
            'sorter': 'invswpac_name',
            'title': u'Software package: Name'
        },
        'invswpac_package_type': {
            'columns': ['invswpac_package_type'],
            'short': u'Type',
            'sorter': 'invswpac_package_type',
            'title': u'Software package: Type'
        },
        'invswpac_package_version': {
            'columns': ['invswpac_package_version'],
            'short': u'Package Version',
            'sorter': 'invswpac_package_version',
            'title': u'Software package: Package Version'
        },
        'invswpac_path': {
            'columns': ['invswpac_path'],
            'short': u'Path',
            'sorter': 'invswpac_path',
            'title': u'Software package: Path'
        },
        'invswpac_size': {
            'columns': ['invswpac_size'],
            'short': u'Size',
            'sorter': 'invswpac_size',
            'title': u'Software package: Size'
        },
        'invswpac_summary': {
            'columns': ['invswpac_summary'],
            'short': u'Description',
            'sorter': 'invswpac_summary',
            'title': u'Software package: Description'
        },
        'invswpac_vendor': {
            'columns': ['invswpac_vendor'],
            'short': u'Publisher',
            'sorter': 'invswpac_vendor',
            'title': u'Software package: Publisher'
        },
        'invswpac_version': {
            'columns': ['invswpac_version'],
            'short': u'Version',
            'sorter': 'invswpac_version',
            'title': u'Software package: Version'
        },
        'invunknown_description': {
            'columns': ['invunknown_description'],
            'short': u'Description',
            'sorter': 'invunknown_description',
            'title': u'Unknown entity: Description'
        },
        'invunknown_index': {
            'columns': ['invunknown_index'],
            'short': u'Index',
            'sorter': 'invunknown_index',
            'title': u'Unknown entity: Index'
        },
        'invunknown_location': {
            'columns': ['invunknown_location'],
            'short': u'Location',
            'sorter': 'invunknown_location',
            'title': u'Unknown entity: Location'
        },
        'invunknown_manufacturer': {
            'columns': ['invunknown_manufacturer'],
            'short': u'Manufacturer',
            'sorter': 'invunknown_manufacturer',
            'title': u'Unknown entity: Manufacturer'
        },
        'invunknown_model': {
            'columns': ['invunknown_model'],
            'short': u'Model Name',
            'sorter': 'invunknown_model',
            'title': u'Unknown entity: Model Name'
        },
        'invunknown_name': {
            'columns': ['invunknown_name'],
            'short': u'Name',
            'sorter': 'invunknown_name',
            'title': u'Unknown entity: Name'
        },
        'invunknown_serial': {
            'columns': ['invunknown_serial'],
            'short': u'Serial Number',
            'sorter': 'invunknown_serial',
            'title': u'Unknown entity: Serial Number'
        },
        'invunknown_software': {
            'columns': ['invunknown_software'],
            'short': u'Software',
            'sorter': 'invunknown_software',
            'title': u'Unknown entity: Software'
        },
        'log_attempt': {
            'columns': ['log_attempt'],
            'short': u'Att.',
            'title': u'Log: number of check attempt'
        },
        'log_command': {
            'columns': ['log_command_name'],
            'short': u'Command',
            'title': u'Log: command/plugin'
        },
        'log_comment': {
            'columns': ['log_options'],
            'short': u'Comment',
            'title': u'Log: comment'
        },
        'log_contact_name': {
            'columns': ['log_contact_name'],
            'short': u'Contact',
            'title': u'Log: contact name'
        },
        'log_date': {
            'columns': ['log_time'],
            'short': u'Date',
            'title': u'Log: day of entry'
        },
        'log_icon': {
            'columns': ['log_type', 'log_state', 'log_state_type', 'log_command_name'],
            'short': '',
            'title': u'Log: event icon'
        },
        'log_lineno': {
            'columns': ['log_lineno'],
            'short': u'Line',
            'title': u'Log: line number in log file'
        },
        'log_message': {
            'columns': ['log_message'],
            'short': u'Message',
            'title': u'Log: complete message'
        },
        'log_options': {
            'columns': ['log_options'],
            'short': u'Info',
            'title': u'Log: informational part of message'
        },
        'log_plugin_output': {
            'columns': [
                'log_plugin_output', 'log_type', 'log_state_type', 'log_comment', 'custom_variables'
            ],
            'short': u'Output',
            'title': u'Log: Output'
        },
        'log_state': {
            'columns': ['log_state', 'log_state_type', 'log_service_description', 'log_type'],
            'short': u'State',
            'title': u'Log: state of host/service at log time'
        },
        'log_state_type': {
            'columns': ['log_state_type'],
            'short': u'Type',
            'title': u'Log: type of state (hard/soft/stopped/started)'
        },
        'log_time': {
            'columns': ['log_time'],
            'options': ['ts_format', 'ts_date'],
            'short': u'Time',
            'title': u'Log: entry time'
        },
        'log_type': {
            'columns': ['log_type'],
            'short': u'Event',
            'title': u'Log: event'
        },
        'log_what': {
            'columns': ['log_type'],
            'short': u'Host/Service',
            'title': u'Log: host or service'
        },
        'num_problems': {
            'columns': ['host_num_services', 'host_num_services_ok', 'host_num_services_pending'],
            'short': u'Pro.',
            'title': u'Number of problems'
        },
        'num_services': {
            'columns': ['host_num_services'],
            'short': '',
            'title': u'Number of services'
        },
        'num_services_crit': {
            'columns': ['host_num_services_crit'],
            'short': u'Cr',
            'title': u'Number of services in state CRIT'
        },
        'num_services_ok': {
            'columns': ['host_num_services_ok'],
            'short': u'OK',
            'title': u'Number of services in state OK'
        },
        'num_services_pending': {
            'columns': ['host_num_services_pending'],
            'short': u'Pd',
            'title': u'Number of services in state PENDING'
        },
        'num_services_unknown': {
            'columns': ['host_num_services_unknown'],
            'short': u'Un',
            'title': u'Number of services in state UNKNOWN'
        },
        'num_services_warn': {
            'columns': ['host_num_services_warn'],
            'short': u'Wa',
            'title': u'Number of services in state WARN'
        },
        'perfometer': {
            'columns': [
                'service_staleness', 'service_perf_data', 'service_state', 'service_check_command',
                'service_pnpgraph_present', 'service_plugin_output'
            ],
            'printable': 'perfometer',
            'short': u'Perf-O-Meter',
            'title': u'Service Perf-O-Meter'
        },
        'service_description': {
            'columns': ['service_description'],
            'short': u'Service',
            'sorter': 'svcdescr',
            'title': u'Service description'
        },
        'service_discovery_check': {
            'columns': ['discovery_state', 'discovery_check', 'discovery_service'],
            'short': u'Check type',
            'title': u'Service discovery: Check type'
        },
        'service_discovery_service': {
            'columns': ['discovery_state', 'discovery_check', 'discovery_service'],
            'short': u'Service description',
            'title': u'Service discovery: Service description'
        },
        'service_discovery_state': {
            'columns': ['discovery_state'],
            'short': u'State',
            'title': u'Service discovery: State'
        },
        'service_display_name': {
            'columns': ['service_display_name'],
            'short': u'Display name',
            'sorter': 'svcdispname',
            'title': u'Service alternative display name'
        },
        'service_graphs': {
            'columns': [
                'host_name', 'service_description', 'service_perf_data', 'service_metrics',
                'service_check_command'
            ],
            'options': ['pnp_timerange', 'graph_render_options'],
            'printable': 'time_graph',
            'title': u'Service Graphs with Timerange Previews'
        },
        'service_icons': {
            'columns': {
                'host_scheduled_downtime_depth',
                'service_check_command',
                'host_downtimes_with_extra_info',
                'site',
                'service_cached_at',
                'service_notifications_enabled',
                'service_downtimes_with_extra_info',
                'host_check_type',
                'service_active_passive_checks',
                'service_in_passive_check_period',
                'service_comments_with_extra_info',
                'service_host_name',
                'service_cache_interval',
                'service_action_url_expanded',
                'service_custom_variable_names',
                'service_perf_data',
                'service_in_service_period',
                'host_check_command',
                'host_filename',
                'service_scheduled_downtime_depth',
                'host_custom_variable_names',
                'service_icon_image',
                'service_notes_url_expanded',
                'service_modified_attributes_list',
                'service_custom_variable_values',
                'service_acknowledged',
                'service_plugin_output',
                'service_staleness',
                'service_description',
                'host_address',
                'service_in_notification_period',
                'service_service_description',
                'service_active_checks_enabled',
                'service_check_type',
                'service_pnpgraph_present',
                'service_in_check_period',
                'host_custom_variable_values',
                'host_name',
                'service_is_flapping',
                'service_state',
            },
            'printable': False,
            'short': u'Icons',
            'title': u'Service icons'
        },
        'service_nagios_link': {
            'columns': ['site', 'host_name', 'service_description'],
            'short': '',
            'title': u'Icon with link to service in Nagios GUI'
        },
        'service_state': {
            'columns': ['service_has_been_checked', 'service_state'],
            'short': u'State',
            'sorter': 'svcstate',
            'title': u'Service state'
        },
        'sg_alias': {
            'columns': ['servicegroup_alias'],
            'short': u'Alias',
            'title': u'Servicegroup alias'
        },
        'sg_name': {
            'columns': ['servicegroup_name'],
            'short': u'Name',
            'title': u'Servicegroup name'
        },
        'sg_num_services': {
            'columns': ['servicegroup_num_services'],
            'short': '',
            'title': u'Number of services (Service Group)'
        },
        'sg_num_services_crit': {
            'columns': ['servicegroup_num_services_crit'],
            'short': u'C',
            'title': u'Number of services in state CRIT (Service Group)'
        },
        'sg_num_services_ok': {
            'columns': ['servicegroup_num_services_ok'],
            'short': u'O',
            'title': u'Number of services in state OK (Service Group)'
        },
        'sg_num_services_pending': {
            'columns': ['servicegroup_num_services_pending'],
            'short': u'P',
            'title': u'Number of services in state PENDING (Service Group)'
        },
        'sg_num_services_unknown': {
            'columns': ['servicegroup_num_services_unknown'],
            'short': u'U',
            'title': u'Number of services in state UNKNOWN (Service Group)'
        },
        'sg_num_services_warn': {
            'columns': ['servicegroup_num_services_warn'],
            'short': u'W',
            'title': u'Number of services in state WARN (Service Group)'
        },
        'sg_services': {
            'columns': ['servicegroup_members_with_state'],
            'short': u'Services',
            'title': u'Services colored according to state (Service Group)'
        },
        'site_icon': {
            'columns': ['site'],
            'short': '',
            'sorter': 'site',
            'title': u'Site icon'
        },
        'sitealias': {
            'columns': ['site'],
            'title': u'Site alias'
        },
        'sitename_plain': {
            'columns': ['site'],
            'short': u'Site',
            'sorter': 'site',
            'title': u'Site ID'
        },
        'sla_fixed': {
            'columns': [
                'host_name', 'host_perf_data', 'host_metrics', 'host_check_command',
                'service_custom_variables'
            ],
            'printable': 'sla_printer',
            'short': ("func", None),
            'title': ("func", None)
        },
        'sla_specific': {
            'columns': [
                'host_name', 'host_perf_data', 'host_metrics', 'host_check_command',
                'service_custom_variables'
            ],
            'printable': 'sla_printer',
            'short': ("func", None),
            'title': ("func", None)
        },
        'svc_acknowledged': {
            'columns': ['service_acknowledged'],
            'short': u'Ack',
            'title': u'Service problem acknowledged'
        },
        'svc_attempt': {
            'columns': ['service_current_attempt', 'service_max_check_attempts'],
            'short': u'Att.',
            'title': u'Current check attempt'
        },
        'svc_check_age': {
            'columns': ['service_has_been_checked', 'service_last_check', 'service_cached_at'],
            'options': ['ts_format', 'ts_date'],
            'short': u'Checked',
            'title': u'The time since the last check of the service'
        },
        'svc_check_cache_info': {
            'columns': ['service_last_check', 'service_cached_at', 'service_cache_interval'],
            'options': ['ts_format', 'ts_date'],
            'short': u'Cached',
            'title': u'Cached agent data'
        },
        'svc_check_command': {
            'columns': ['service_check_command'],
            'short': u'Check command',
            'title': u'Service check command'
        },
        'svc_check_command_expanded': {
            'columns': ['service_check_command_expanded'],
            'short': u'Check command expanded',
            'title': u'Service check command expanded'
        },
        'svc_check_duration': {
            'columns': ['service_execution_time'],
            'short': u'Duration',
            'title': u'Service check duration'
        },
        'svc_check_interval': {
            'columns': ['service_check_interval', 'service_retry_interval'],
            'short': u'Interval',
            'title': u'Service normal/retry check interval'
        },
        'svc_check_latency': {
            'columns': ['service_latency'],
            'short': u'Latency',
            'title': u'Service check latency'
        },
        'svc_check_period': {
            'columns': ['service_check_period'],
            'short': u'check.',
            'title': u'Service check period'
        },
        'svc_check_type': {
            'columns': ['service_check_type'],
            'short': u'Type',
            'title': u'Service check type'
        },
        'svc_comments': {
            'columns': ['service_comments_with_info'],
            'short': u'Comments',
            'title': u'Service Comments'
        },
        'svc_contact_groups': {
            'columns': ['service_contact_groups'],
            'short': u'Contact groups',
            'title': u'Service contact groups'
        },
        'svc_contacts': {
            'columns': ['service_contacts'],
            'short': u'Contacts',
            'title': u'Service contacts'
        },
        'svc_custom_notes': {
            'columns': [
                'host_name', 'host_address', 'service_description', 'service_plugin_output'
            ],
            'short': u'Notes',
            'title': u'Custom services notes'
        },
        'svc_custom_vars': {
            'columns': ['service_custom_variables'],
            'title': u'Service custom variables'
        },
        'svc_flapping': {
            'columns': ['service_is_flapping'],
            'short': u'Flap',
            'title': u'Service is flapping'
        },
        'svc_group_memberlist': {
            'columns': ['service_groups'],
            'short': u'Groups',
            'title': u'Service groups the service is member of'
        },
        'svc_in_downtime': {
            'columns': ['service_scheduled_downtime_depth'],
            'short': u'Dt.',
            'title': u'Currently in downtime'
        },
        'svc_in_notifper': {
            'columns': ['service_in_notification_period'],
            'short': u'in notif. p.',
            'title': u'In notification period'
        },
        'svc_is_active': {
            'columns': ['service_active_checks_enabled'],
            'short': u'Active',
            'title': u'Service is active'
        },
        'svc_is_stale': {
            'columns': ['service_staleness'],
            'short': u'Stale',
            'sorter': 'svc_staleness',
            'title': u'Service is stale'
        },
        'svc_last_notification': {
            'columns': ['service_last_notification'],
            'options': ['ts_format', 'ts_date'],
            'short': u'last notification',
            'title': u'The time of the last service notification'
        },
        'svc_last_time_ok': {
            'columns': ['service_last_time_ok', 'service_has_been_checked'],
            'short': u'Last OK',
            'title': u'The last time the service was OK'
        },
        'svc_long_plugin_output': {
            'columns': ['service_long_plugin_output', 'service_custom_variables'],
            'short': u'Details',
            'title': u'Details',
        },
        'svc_metrics': {
            'columns': ['service_check_command', 'service_perf_data'],
            'printable': False,
            'short': u'Metrics',
            'title': u'Service Metrics'
        },
        'svc_next_check': {
            'columns': ['service_next_check'],
            'short': u'Next check',
            'title': u'The time of the next scheduled service check'
        },
        'svc_next_notification': {
            'columns': ['service_next_notification'],
            'short': u'Next notification',
            'title': u'The time of the next service notification'
        },
        'svc_normal_interval': {
            'columns': ['service_check_interval'],
            'short': u'Check int.',
            'title': u'Service normal check interval'
        },
        'svc_notification_number': {
            'columns': ['service_current_notification_number'],
            'short': u'N#',
            'title': u'Service notification number'
        },
        'svc_notification_postponement_reason': {
            'columns': ['service_notification_postponement_reason'],
            'short': u'Notif. postponed',
            'title': u'Notification postponement reason'
        },
        'svc_notifications_enabled': {
            'columns': ['service_notifications_enabled'],
            'short': u'Notif.',
            'title': u'Service notifications enabled'
        },
        'svc_notifper': {
            'columns': ['service_notification_period'],
            'short': u'notif.',
            'title': u'Service notification period'
        },
        'svc_perf_data': {
            'columns': ['service_perf_data'],
            'short': u'Perfdata',
            'title': u'Service performance data (source code)'
        },
        'svc_perf_val01': {
            'columns': ['service_perf_data'],
            'short': u'Val. 1',
            'title': u'Service performance data - value number  1'
        },
        'svc_perf_val02': {
            'columns': ['service_perf_data'],
            'short': u'Val. 2',
            'title': u'Service performance data - value number  2'
        },
        'svc_perf_val03': {
            'columns': ['service_perf_data'],
            'short': u'Val. 3',
            'title': u'Service performance data - value number  3'
        },
        'svc_perf_val04': {
            'columns': ['service_perf_data'],
            'short': u'Val. 4',
            'title': u'Service performance data - value number  4'
        },
        'svc_perf_val05': {
            'columns': ['service_perf_data'],
            'short': u'Val. 5',
            'title': u'Service performance data - value number  5'
        },
        'svc_perf_val06': {
            'columns': ['service_perf_data'],
            'short': u'Val. 6',
            'title': u'Service performance data - value number  6'
        },
        'svc_perf_val07': {
            'columns': ['service_perf_data'],
            'short': u'Val. 7',
            'title': u'Service performance data - value number  7'
        },
        'svc_perf_val08': {
            'columns': ['service_perf_data'],
            'short': u'Val. 8',
            'title': u'Service performance data - value number  8'
        },
        'svc_perf_val09': {
            'columns': ['service_perf_data'],
            'short': u'Val. 9',
            'title': u'Service performance data - value number  9'
        },
        'svc_perf_val10': {
            'columns': ['service_perf_data'],
            'short': u'Val. 10',
            'title': u'Service performance data - value number 10'
        },
        'svc_plugin_output': {
            'columns': ['service_plugin_output', 'service_custom_variables'],
            'short': u'Summary',
            'sorter': 'svcoutput',
            'title': u'Summary'
        },
        'svc_pnpgraph': {
            'columns': [
                'host_name', 'service_description', 'service_perf_data', 'service_metrics',
                'service_check_command'
            ],
            'options': ['pnp_timerange'],
            'printable': 'time_graph',
            'title': u'Service Graphs'
        },
        'svc_retry_interval': {
            'columns': ['service_retry_interval'],
            'short': u'Retry',
            'title': u'Service retry check interval'
        },
        'svc_servicelevel': {
            'columns': ['service_custom_variable_names', 'service_custom_variable_values'],
            'short': u'Service Level',
            'sorter': 'servicelevel',
            'title': u'Service service level'
        },
        'svc_staleness': {
            'columns': ['service_staleness'],
            'short': u'Staleness',
            'title': u'Service staleness value'
        },
        'svc_state_age': {
            'columns': ['service_has_been_checked', 'service_last_state_change'],
            'options': ['ts_format', 'ts_date'],
            'short': u'Age',
            'sorter': 'stateage',
            'title': u'The age of the current service state'
        },
        'wato_folder_abs': {
            'columns': ['host_filename'],
            'short': u'WATO folder',
            'sorter': 'wato_folder_abs',
            'title': u'WATO folder - complete path'
        },
        'wato_folder_plain': {
            'columns': ['host_filename'],
            'short': u'WATO folder',
            'sorter': 'wato_folder_plain',
            'title': u'WATO folder - just folder name'
        },
        'wato_folder_rel': {
            'columns': ['host_filename'],
            'short': u'WATO folder',
            'sorter': 'wato_folder_rel',
            'title': u'WATO folder - relative path'
        },
        'inv': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'options': ['show_internal_tree_paths'],
            'short': u'Inventory',
            'sorter': 'inv',
            'title': u'Inventory Tree'
        },
        'inv_hardware': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'options': ['show_internal_tree_paths'],
            'short': u'Hardware',
            'sorter': 'inv_hardware',
            'title': u'Inventory: Inventory \u27a4 Hardware'
        },
        'inv_hardware_chassis': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'options': ['show_internal_tree_paths'],
            'short': u'Chassis',
            'sorter': 'inv_hardware_chassis',
            'title': u'Inventory: Hardware \u27a4 Chassis'
        },
        'inv_hardware_components': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'options': ['show_internal_tree_paths'],
            'short': u'Physical Components',
            'sorter': 'inv_hardware_components',
            'title': u'Inventory: Hardware \u27a4 Physical Components'
        },
        'inv_hardware_components_backplanes': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'options': ['show_internal_tree_paths'],
            'short': u'Backplanes',
            'sorter': 'inv_hardware_components_backplanes',
            'title': u'Inventory: Physical Components \u27a4 Backplanes'
        },
        'inv_hardware_components_chassis': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'options': ['show_internal_tree_paths'],
            'short': u'Chassis',
            'sorter': 'inv_hardware_components_chassis',
            'title': u'Inventory: Physical Components \u27a4 Chassis'
        },
        'inv_hardware_components_containers': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'options': ['show_internal_tree_paths'],
            'short': u'Containers',
            'sorter': 'inv_hardware_components_containers',
            'title': u'Inventory: Physical Components \u27a4 Containers'
        },
        'inv_hardware_components_fans': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'options': ['show_internal_tree_paths'],
            'short': u'Fans',
            'sorter': 'inv_hardware_components_fans',
            'title': u'Inventory: Physical Components \u27a4 Fans'
        },
        'inv_hardware_components_modules': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'options': ['show_internal_tree_paths'],
            'short': u'Modules',
            'sorter': 'inv_hardware_components_modules',
            'title': u'Inventory: Physical Components \u27a4 Modules'
        },
        'inv_hardware_components_others': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'options': ['show_internal_tree_paths'],
            'short': u'Other entities',
            'sorter': 'inv_hardware_components_others',
            'title': u'Inventory: Physical Components \u27a4 Other entities'
        },
        'inv_hardware_components_psus': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'options': ['show_internal_tree_paths'],
            'short': u'Power Supplies',
            'sorter': 'inv_hardware_components_psus',
            'title': u'Inventory: Physical Components \u27a4 Power Supplies'
        },
        'inv_hardware_components_sensors': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'options': ['show_internal_tree_paths'],
            'short': u'Sensors',
            'sorter': 'inv_hardware_components_sensors',
            'title': u'Inventory: Physical Components \u27a4 Sensors'
        },
        'inv_hardware_components_stacks': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'options': ['show_internal_tree_paths'],
            'short': u'Stacks',
            'sorter': 'inv_hardware_components_stacks',
            'title': u'Inventory: Physical Components \u27a4 Stacks'
        },
        'inv_hardware_components_unknowns': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'options': ['show_internal_tree_paths'],
            'short': u'Unknown entities',
            'sorter': 'inv_hardware_components_unknowns',
            'title': u'Inventory: Physical Components \u27a4 Unknown entities'
        },
        'inv_hardware_cpu': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'options': ['show_internal_tree_paths'],
            'short': u'Processor',
            'sorter': 'inv_hardware_cpu',
            'title': u'Inventory: Hardware \u27a4 Processor'
        },
        'inv_hardware_cpu_arch': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'options': ['show_internal_tree_paths'],
            'short': u'CPU Arch',
            'sorter': 'inv_hardware_cpu_arch',
            'title': u'Inventory: Processor \u27a4 CPU Architecture'
        },
        'inv_hardware_cpu_bus_speed': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'options': ['show_internal_tree_paths'],
            'short': u'Bus Speed',
            'sorter': 'inv_hardware_cpu_bus_speed',
            'title': u'Inventory: Processor \u27a4 Bus Speed'
        },
        'inv_hardware_cpu_cache_size': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'options': ['show_internal_tree_paths'],
            'short': u'Cache Size',
            'sorter': 'inv_hardware_cpu_cache_size',
            'title': u'Inventory: Processor \u27a4 Cache Size'
        },
        'inv_hardware_cpu_cores': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'options': ['show_internal_tree_paths'],
            'short': u'Cores',
            'sorter': 'inv_hardware_cpu_cores',
            'title': u'Inventory: Processor \u27a4 Total Number of Cores'
        },
        'inv_hardware_cpu_cores_per_cpu': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'options': ['show_internal_tree_paths'],
            'short': u'Cores per CPU',
            'sorter': 'inv_hardware_cpu_cores_per_cpu',
            'title': u'Inventory: Processor \u27a4 Cores per CPU'
        },
        'inv_hardware_cpu_cpus': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'options': ['show_internal_tree_paths'],
            'short': u'CPUs',
            'sorter': 'inv_hardware_cpu_cpus',
            'title': u'Inventory: Processor \u27a4 Number of physical CPUs'
        },
        'inv_hardware_cpu_entitlement': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'options': ['show_internal_tree_paths'],
            'short': u'CPU Entitlement',
            'sorter': 'inv_hardware_cpu_entitlement',
            'title': u'Inventory: Processor \u27a4 CPU Entitlement'
        },
        'inv_hardware_cpu_logical_cpus': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'options': ['show_internal_tree_paths'],
            'short': u'Logical CPUs',
            'sorter': 'inv_hardware_cpu_logical_cpus',
            'title': u'Inventory: Processor \u27a4 Number of logical CPUs'
        },
        'inv_hardware_cpu_max_speed': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'options': ['show_internal_tree_paths'],
            'short': u'Maximum Speed',
            'sorter': 'inv_hardware_cpu_max_speed',
            'title': u'Inventory: Processor \u27a4 Maximum Speed'
        },
        'inv_hardware_cpu_model': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'options': ['show_internal_tree_paths'],
            'short': u'CPU Model',
            'sorter': 'inv_hardware_cpu_model',
            'title': u'Inventory: Processor \u27a4 Model'
        },
        'inv_hardware_cpu_sharing_mode': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'options': ['show_internal_tree_paths'],
            'short': u'CPU sharing mode',
            'sorter': 'inv_hardware_cpu_sharing_mode',
            'title': u'Inventory: Processor \u27a4 CPU sharing mode'
        },
        'inv_hardware_cpu_smt_threads': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'options': ['show_internal_tree_paths'],
            'short': u'Simultaneous multithreading',
            'sorter': 'inv_hardware_cpu_smt_threads',
            'title': u'Inventory: Processor \u27a4 Simultaneous multithreading'
        },
        'inv_hardware_cpu_threads': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'options': ['show_internal_tree_paths'],
            'short': u'Total Number of Hyperthreads',
            'sorter': 'inv_hardware_cpu_threads',
            'title': u'Inventory: Processor \u27a4 Total Number of Hyperthreads'
        },
        'inv_hardware_cpu_threads_per_cpu': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'options': ['show_internal_tree_paths'],
            'short': u'Hyperthreads per CPU',
            'sorter': 'inv_hardware_cpu_threads_per_cpu',
            'title': u'Inventory: Processor \u27a4 Hyperthreads per CPU'
        },
        'inv_hardware_cpu_voltage': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'options': ['show_internal_tree_paths'],
            'short': u'Voltage',
            'sorter': 'inv_hardware_cpu_voltage',
            'title': u'Inventory: Processor \u27a4 Voltage'
        },
        'inv_hardware_memory': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'options': ['show_internal_tree_paths'],
            'short': u'Memory (RAM)',
            'sorter': 'inv_hardware_memory',
            'title': u'Inventory: Hardware \u27a4 Memory (RAM)'
        },
        'inv_hardware_memory_arrays': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'options': ['show_internal_tree_paths'],
            'short': u'Arrays (Controllers)',
            'sorter': 'inv_hardware_memory_arrays',
            'title': u'Inventory: Memory (RAM) \u27a4 Arrays (Controllers)'
        },
        'inv_hardware_memory_total_ram_usable': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'options': ['show_internal_tree_paths'],
            'short': u'Total usable RAM',
            'sorter': 'inv_hardware_memory_total_ram_usable',
            'title': u'Inventory: Memory (RAM) \u27a4 Total usable RAM'
        },
        'inv_hardware_memory_total_swap': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'options': ['show_internal_tree_paths'],
            'short': u'Total swap space',
            'sorter': 'inv_hardware_memory_total_swap',
            'title': u'Inventory: Memory (RAM) \u27a4 Total swap space'
        },
        'inv_hardware_memory_total_vmalloc': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'options': ['show_internal_tree_paths'],
            'short': u'Virtual addresses for mapping',
            'sorter': 'inv_hardware_memory_total_vmalloc',
            'title': u'Inventory: Memory (RAM) \u27a4 Virtual addresses for mapping'
        },
        'inv_hardware_nwadapter': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'options': ['show_internal_tree_paths'],
            'short': u'Network Adapters',
            'sorter': 'inv_hardware_nwadapter',
            'title': u'Inventory: Hardware \u27a4 Network Adapters'
        },
        'inv_hardware_storage': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'options': ['show_internal_tree_paths'],
            'short': u'Storage',
            'sorter': 'inv_hardware_storage',
            'title': u'Inventory: Hardware \u27a4 Storage'
        },
        'inv_hardware_storage_controller': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'options': ['show_internal_tree_paths'],
            'short': u'Controller',
            'sorter': 'inv_hardware_storage_controller',
            'title': u'Inventory: Storage \u27a4 Controller'
        },
        'inv_hardware_storage_controller_version': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'options': ['show_internal_tree_paths'],
            'short': u'Version',
            'sorter': 'inv_hardware_storage_controller_version',
            'title': u'Inventory: Controller \u27a4 Version'
        },
        'inv_hardware_storage_disks': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'options': ['show_internal_tree_paths'],
            'short': u'Block Devices',
            'sorter': 'inv_hardware_storage_disks',
            'title': u'Inventory: Storage \u27a4 Block Devices'
        },
        'inv_hardware_system': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'options': ['show_internal_tree_paths'],
            'short': u'System',
            'sorter': 'inv_hardware_system',
            'title': u'Inventory: Hardware \u27a4 System'
        },
        'inv_hardware_system_expresscode': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'options': ['show_internal_tree_paths'],
            'short': u'Express Servicecode',
            'sorter': 'inv_hardware_system_expresscode',
            'title': u'Inventory: System \u27a4 Express Servicecode'
        },
        'inv_hardware_system_manufacturer': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'options': ['show_internal_tree_paths'],
            'short': u'Manufacturer',
            'sorter': 'inv_hardware_system_manufacturer',
            'title': u'Inventory: System \u27a4 Manufacturer'
        },
        'inv_hardware_system_model': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'options': ['show_internal_tree_paths'],
            'short': u'Model Name',
            'sorter': 'inv_hardware_system_model',
            'title': u'Inventory: System \u27a4 Model Name'
        },
        'inv_hardware_system_model_name': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'options': ['show_internal_tree_paths'],
            'short': u"Model Name - LEGACY, don't use",
            'sorter': 'inv_hardware_system_model_name',
            'title': u"Inventory: System \u27a4 Model Name - LEGACY, don't use"
        },
        'inv_hardware_system_product': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'options': ['show_internal_tree_paths'],
            'short': u'Product',
            'sorter': 'inv_hardware_system_product',
            'title': u'Inventory: System \u27a4 Product'
        },
        'inv_hardware_system_serial': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'options': ['show_internal_tree_paths'],
            'short': u'Serial Number',
            'sorter': 'inv_hardware_system_serial',
            'title': u'Inventory: System \u27a4 Serial Number'
        },
        'inv_hardware_system_serial_number': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'options': ['show_internal_tree_paths'],
            'short': u"Serial Number - LEGACY, don't use",
            'sorter': 'inv_hardware_system_serial_number',
            'title': u"Inventory: System \u27a4 Serial Number - LEGACY, don't use"
        },
        'inv_hardware_video': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'options': ['show_internal_tree_paths'],
            'short': u'Graphic Cards',
            'sorter': 'inv_hardware_video',
            'title': u'Inventory: Hardware \u27a4 Graphic Cards'
        },
        'inv_networking': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'options': ['show_internal_tree_paths'],
            'short': u'Networking',
            'sorter': 'inv_networking',
            'title': u'Inventory: Inventory \u27a4 Networking'
        },
        'inv_networking_addresses': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'options': ['show_internal_tree_paths'],
            'short': u'IP Addresses',
            'sorter': 'inv_networking_addresses',
            'title': u'Inventory: Networking \u27a4 IP Addresses'
        },
        'inv_networking_available_ethernet_ports': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'options': ['show_internal_tree_paths'],
            'short': u'Ports available',
            'sorter': 'inv_networking_available_ethernet_ports',
            'title': u'Inventory: Networking \u27a4 Ports available'
        },
        'inv_networking_interfaces': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'options': ['show_internal_tree_paths'],
            'short': u'Interfaces',
            'sorter': 'inv_networking_interfaces',
            'title': u'Inventory: Networking \u27a4 Interfaces'
        },
        'inv_networking_routes': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'options': ['show_internal_tree_paths'],
            'short': u'Routes',
            'sorter': 'inv_networking_routes',
            'title': u'Inventory: Networking \u27a4 Routes'
        },
        'inv_networking_total_ethernet_ports': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'options': ['show_internal_tree_paths'],
            'short': u'Ports',
            'sorter': 'inv_networking_total_ethernet_ports',
            'title': u'Inventory: Networking \u27a4 Ports'
        },
        'inv_networking_total_interfaces': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'options': ['show_internal_tree_paths'],
            'short': u'Interfaces',
            'sorter': 'inv_networking_total_interfaces',
            'title': u'Inventory: Networking \u27a4 Interfaces'
        },
        'inv_networking_wlan': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'options': ['show_internal_tree_paths'],
            'short': u'WLAN',
            'sorter': 'inv_networking_wlan',
            'title': u'Inventory: Networking \u27a4 WLAN'
        },
        'inv_networking_wlan_controller': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'options': ['show_internal_tree_paths'],
            'short': u'Controller',
            'sorter': 'inv_networking_wlan_controller',
            'title': u'Inventory: WLAN \u27a4 Controller'
        },
        'inv_networking_wlan_controller_accesspoints': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'options': ['show_internal_tree_paths'],
            'short': u'Access Points',
            'sorter': 'inv_networking_wlan_controller_accesspoints',
            'title': u'Inventory: Controller \u27a4 Access Points'
        },
        'inv_software': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'options': ['show_internal_tree_paths'],
            'short': u'Software',
            'sorter': 'inv_software',
            'title': u'Inventory: Inventory \u27a4 Software'
        },
        'inv_software_applications': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'options': ['show_internal_tree_paths'],
            'short': u'Applications',
            'sorter': 'inv_software_applications',
            'title': u'Inventory: Software \u27a4 Applications'
        },
        'inv_software_applications_check_mk': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'options': ['show_internal_tree_paths'],
            'short': u'Check_MK',
            'sorter': 'inv_software_applications_check_mk',
            'title': u'Inventory: Applications \u27a4 Check_MK'
        },
        'inv_software_applications_check_mk_cluster_is_cluster': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'options': ['show_internal_tree_paths'],
            'short': u'Cluster',
            'sorter': 'inv_software_applications_check_mk_cluster_is_cluster',
            'title': u'Inventory: Cluster \u27a4 Cluster host'
        },
        'inv_software_applications_check_mk_cluster_nodes': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'options': ['show_internal_tree_paths'],
            'short': u'Nodes',
            'sorter': 'inv_software_applications_check_mk_cluster_nodes',
            'title': u'Inventory: Cluster \u27a4 Nodes'
        },
        'inv_software_applications_citrix': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'options': ['show_internal_tree_paths'],
            'short': u'Citrix',
            'sorter': 'inv_software_applications_citrix',
            'title': u'Inventory: Applications \u27a4 Citrix'
        },
        'inv_software_applications_citrix_controller': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'options': ['show_internal_tree_paths'],
            'short': u'Controller',
            'sorter': 'inv_software_applications_citrix_controller',
            'title': u'Inventory: Citrix \u27a4 Controller'
        },
        'inv_software_applications_citrix_controller_controller_version': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'options': ['show_internal_tree_paths'],
            'short': u'Controller Version',
            'sorter': 'inv_software_applications_citrix_controller_controller_version',
            'title': u'Inventory: Controller \u27a4 Controller Version'
        },
        'inv_software_applications_citrix_vm': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'options': ['show_internal_tree_paths'],
            'short': u'Virtual Machine',
            'sorter': 'inv_software_applications_citrix_vm',
            'title': u'Inventory: Citrix \u27a4 Virtual Machine'
        },
        'inv_software_applications_citrix_vm_agent_version': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'options': ['show_internal_tree_paths'],
            'short': u'Agent Version',
            'sorter': 'inv_software_applications_citrix_vm_agent_version',
            'title': u'Inventory: Virtual Machine \u27a4 Agent Version'
        },
        'inv_software_applications_citrix_vm_catalog': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'options': ['show_internal_tree_paths'],
            'short': u'Catalog',
            'sorter': 'inv_software_applications_citrix_vm_catalog',
            'title': u'Inventory: Virtual Machine \u27a4 Catalog'
        },
        'inv_software_applications_citrix_vm_desktop_group_name': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'options': ['show_internal_tree_paths'],
            'short': u'Desktop Group Name',
            'sorter': 'inv_software_applications_citrix_vm_desktop_group_name',
            'title': u'Inventory: Virtual Machine \u27a4 Desktop Group Name'
        },
        'inv_software_applications_docker': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'options': ['show_internal_tree_paths'],
            'short': 'Docker',
            'sorter': 'inv_software_applications_docker',
            'title': u'Inventory: Applications \u27a4 Docker'
        },
        'inv_software_applications_docker_container': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'options': ['show_internal_tree_paths'],
            'short': u'Container',
            'sorter': 'inv_software_applications_docker_container',
            'title': u'Inventory: Docker \u27a4 Container'
        },
        'inv_software_applications_docker_container_networks': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'options': ['show_internal_tree_paths'],
            'short': u'Networks',
            'sorter': 'inv_software_applications_docker_container_networks',
            'title': u'Inventory: Container \u27a4 Networks'
        },
        'inv_software_applications_docker_container_node_name': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'options': ['show_internal_tree_paths'],
            'short': u'Node name',
            'sorter': 'inv_software_applications_docker_container_node_name',
            'title': u'Inventory: Container \u27a4 Node name'
        },
        'inv_software_applications_docker_container_ports': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'options': ['show_internal_tree_paths'],
            'short': u'Ports',
            'sorter': 'inv_software_applications_docker_container_ports',
            'title': u'Inventory: Container \u27a4 Ports'
        },
        'inv_software_applications_docker_containers': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'options': ['show_internal_tree_paths'],
            'short': u'Containers',
            'sorter': 'inv_software_applications_docker_containers',
            'title': u'Inventory: Docker \u27a4 Containers'
        },
        'inv_software_applications_docker_images': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'options': ['show_internal_tree_paths'],
            'short': u'Images',
            'sorter': 'inv_software_applications_docker_images',
            'title': u'Inventory: Docker \u27a4 Images'
        },
        'inv_software_applications_docker_num_containers_paused': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'options': ['show_internal_tree_paths'],
            'short': u'# Containers paused',
            'sorter': 'inv_software_applications_docker_num_containers_paused',
            'title': u'Inventory: Docker \u27a4 # Containers paused'
        },
        'inv_software_applications_docker_num_containers_running': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'options': ['show_internal_tree_paths'],
            'short': u'# Containers running',
            'sorter': 'inv_software_applications_docker_num_containers_running',
            'title': u'Inventory: Docker \u27a4 # Containers running'
        },
        'inv_software_applications_docker_num_containers_stopped': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'options': ['show_internal_tree_paths'],
            'short': u'# Containers stopped',
            'sorter': 'inv_software_applications_docker_num_containers_stopped',
            'title': u'Inventory: Docker \u27a4 # Containers stopped'
        },
        'inv_software_applications_docker_num_containers_total': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'options': ['show_internal_tree_paths'],
            'short': u'# Containers',
            'sorter': 'inv_software_applications_docker_num_containers_total',
            'title': u'Inventory: Docker \u27a4 # Containers'
        },
        'inv_software_applications_docker_num_images': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'options': ['show_internal_tree_paths'],
            'short': u'# Images',
            'sorter': 'inv_software_applications_docker_num_images',
            'title': u'Inventory: Docker \u27a4 # Images'
        },
        'inv_software_applications_kubernetes_nodes': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'options': ['show_internal_tree_paths'],
            'short': u'Nodes',
            'sorter': 'inv_software_applications_kubernetes_nodes',
            'title': u'Inventory: Kubernetes \u27a4 Nodes',
        },
        'inv_software_applications_kubernetes_roles': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'options': ['show_internal_tree_paths'],
            'short': u'Roles',
            'sorter': 'inv_software_applications_kubernetes_roles',
            'title': u'Inventory: Kubernetes \u27a4 Roles',
        },
        'inv_software_applications_mssql': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'options': ['show_internal_tree_paths'],
            'short': u'MSSQL',
            'sorter': 'inv_software_applications_mssql',
            'title': u'Inventory: Applications \u27a4 MSSQL'
        },
        'inv_software_applications_mssql_instances': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'options': ['show_internal_tree_paths'],
            'short': u'Instances',
            'sorter': 'inv_software_applications_mssql_instances',
            'title': u'Inventory: MSSQL \u27a4 Instances'
        },
        'inv_software_applications_oracle': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'options': ['show_internal_tree_paths'],
            'short': u'Oracle DB',
            'sorter': 'inv_software_applications_oracle',
            'title': u'Inventory: Applications \u27a4 Oracle DB'
        },
        'inv_software_applications_oracle_dataguard_stats': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'options': ['show_internal_tree_paths'],
            'short': u'Dataguard statistics',
            'sorter': 'inv_software_applications_oracle_dataguard_stats',
            'title': u'Inventory: Oracle DB \u27a4 Dataguard statistics'
        },
        'inv_software_applications_oracle_instance': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'options': ['show_internal_tree_paths'],
            'short': u'Instances',
            'sorter': 'inv_software_applications_oracle_instance',
            'title': u'Inventory: Oracle DB \u27a4 Instances'
        },
        'inv_software_applications_oracle_recovery_area': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'options': ['show_internal_tree_paths'],
            'short': u'Recovery area',
            'sorter': 'inv_software_applications_oracle_recovery_area',
            'title': u'Inventory: Oracle DB \u27a4 Recovery area'
        },
        'inv_software_applications_oracle_sga': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'options': ['show_internal_tree_paths'],
            'short': u'SGA Info',
            'sorter': 'inv_software_applications_oracle_sga',
            'title': u'Inventory: Oracle DB \u27a4 SGA Info'
        },
        'inv_software_applications_oracle_tablespaces': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'options': ['show_internal_tree_paths'],
            'short': u'Tablespaces',
            'sorter': 'inv_software_applications_oracle_tablespaces',
            'title': u'Inventory: Oracle DB \u27a4 Tablespaces'
        },
        'inv_software_bios': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'options': ['show_internal_tree_paths'],
            'short': u'BIOS',
            'sorter': 'inv_software_bios',
            'title': u'Inventory: Software \u27a4 BIOS'
        },
        'inv_software_bios_date': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'options': ['show_internal_tree_paths'],
            'short': u'Date',
            'sorter': 'inv_software_bios_date',
            'title': u'Inventory: BIOS \u27a4 Date'
        },
        'inv_software_bios_vendor': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'options': ['show_internal_tree_paths'],
            'short': u'Vendor',
            'sorter': 'inv_software_bios_vendor',
            'title': u'Inventory: BIOS \u27a4 Vendor'
        },
        'inv_software_bios_version': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'options': ['show_internal_tree_paths'],
            'short': u'Version',
            'sorter': 'inv_software_bios_version',
            'title': u'Inventory: BIOS \u27a4 Version'
        },
        'inv_software_configuration': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'options': ['show_internal_tree_paths'],
            'short': u'Configuration',
            'sorter': 'inv_software_configuration',
            'title': u'Inventory: Software \u27a4 Configuration'
        },
        'inv_software_configuration_snmp_info': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'options': ['show_internal_tree_paths'],
            'short': u'SNMP Information',
            'sorter': 'inv_software_configuration_snmp_info',
            'title': u'Inventory: Configuration \u27a4 SNMP Information'
        },
        'inv_software_configuration_snmp_info_contact': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'options': ['show_internal_tree_paths'],
            'short': u'Contact',
            'sorter': 'inv_software_configuration_snmp_info_contact',
            'title': u'Inventory: SNMP Information \u27a4 Contact'
        },
        'inv_software_configuration_snmp_info_location': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'options': ['show_internal_tree_paths'],
            'short': u'Location',
            'sorter': 'inv_software_configuration_snmp_info_location',
            'title': u'Inventory: SNMP Information \u27a4 Location'
        },
        'inv_software_configuration_snmp_info_name': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'options': ['show_internal_tree_paths'],
            'short': u'System name',
            'sorter': 'inv_software_configuration_snmp_info_name',
            'title': u'Inventory: SNMP Information \u27a4 System name'
        },
        'inv_software_firmware_platform_level': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'options': ['show_internal_tree_paths'],
            'short': u'Platform Firmware level',
            'sorter': 'inv_software_firmware_platform_level',
            'title': u'Inventory: Firmware \u27a4 Platform Firmware level'
        },
        'inv_software_firmware_vendor': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'options': ['show_internal_tree_paths'],
            'short': u'Vendor',
            'sorter': 'inv_software_firmware_vendor',
            'title': u'Inventory: Firmware \u27a4 Vendor'
        },
        'inv_software_firmware_version': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'options': ['show_internal_tree_paths'],
            'short': u'Version',
            'sorter': 'inv_software_firmware_version',
            'title': u'Inventory: Firmware \u27a4 Version'
        },
        'inv_software_os': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'options': ['show_internal_tree_paths'],
            'short': u'Operating System',
            'sorter': 'inv_software_os',
            'title': u'Inventory: Software \u27a4 Operating System'
        },
        'inv_software_os_arch': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'options': ['show_internal_tree_paths'],
            'short': u'Architecture',
            'sorter': 'inv_software_os_arch',
            'title': u'Inventory: Operating System \u27a4 Kernel Architecture'
        },
        'inv_software_os_install_date': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'options': ['show_internal_tree_paths'],
            'short': u'Install Date',
            'sorter': 'inv_software_os_install_date',
            'title': u'Inventory: Operating System \u27a4 Install Date'
        },
        'inv_software_os_kernel_version': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'options': ['show_internal_tree_paths'],
            'short': u'Kernel',
            'sorter': 'inv_software_os_kernel_version',
            'title': u'Inventory: Operating System \u27a4 Kernel Version'
        },
        'inv_software_os_name': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'options': ['show_internal_tree_paths'],
            'short': u'Operating System',
            'sorter': 'inv_software_os_name',
            'title': u'Inventory: Operating System \u27a4 Name'
        },
        'inv_software_os_service_pack': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'options': ['show_internal_tree_paths'],
            'short': u'Service Pack',
            'sorter': 'inv_software_os_service_pack',
            'title': u'Inventory: Operating System \u27a4 Latest Service Pack'
        },
        'inv_software_os_service_packs': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'options': ['show_internal_tree_paths'],
            'short': u'Service Packs',
            'sorter': 'inv_software_os_service_packs',
            'title': u'Inventory: Operating System \u27a4 Service Packs'
        },
        'inv_software_os_type': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'options': ['show_internal_tree_paths'],
            'short': u'Type',
            'sorter': 'inv_software_os_type',
            'title': u'Inventory: Operating System \u27a4 Type'
        },
        'inv_software_os_vendor': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'options': ['show_internal_tree_paths'],
            'short': u'Vendor',
            'sorter': 'inv_software_os_vendor',
            'title': u'Inventory: Operating System \u27a4 Vendor'
        },
        'inv_software_os_version': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'options': ['show_internal_tree_paths'],
            'short': u'Version',
            'sorter': 'inv_software_os_version',
            'title': u'Inventory: Operating System \u27a4 Version'
        },
        'inv_software_packages': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'options': ['show_internal_tree_paths'],
            'short': u'Packages',
            'sorter': 'inv_software_packages',
            'title': u'Inventory: Software \u27a4 Packages'
        },
    }

    #xx = {}
    #for ident, p in cmk.gui.plugins.views.multisite_painters.items():
    #    if ident == "inv" or ident.startswith("inv_"):
    #        del p["paint"]
    #        try:
    #            del p["groupby"]
    #        except KeyError:
    #            pass
    #        try:
    #            del p["params"]
    #        except KeyError:
    #            pass
    #        xx[ident] = p

    #import pprint
    #x = pprint.pformat(xx)
    #open("/tmp/x", "w").write(x)

    names = cmk.gui.plugins.views.painter_registry.keys()
    assert sorted(expected.keys()) == sorted(names)

    known_keys = {
        "title",
        "columns",
        "short",
        "sorter",
        "options",
        "printable",
        "load_inv",
    }
    for spec in expected.values():
        this_keys = set(spec.keys())
        assert not this_keys.difference(known_keys)

    for painter_class in cmk.gui.plugins.views.painter_registry.values():
        painter = painter_class()
        spec = expected[painter.ident]

        assert painter.title == spec["title"]

        if isinstance(spec["columns"], tuple) and spec["columns"][0] == "func":
            assert hasattr(painter.columns, '__call__')
        else:
            assert painter.columns == spec["columns"]

        assert painter.short_title == spec.get("short", spec["title"])

        assert painter.sorter == spec.get("sorter")
        assert painter.painter_options == spec.get("options", [])
        assert painter.printable == spec.get("printable", True)
        assert painter.load_inv == spec.get("load_inv", False)

def test_painter_export_title(monkeypatch) -> None:
    painters: list[Painter] = [painter_class() for painter_class in cmk.gui.plugins.views.painter_registry.values()]
    painters_and_cells: list[Tuple[Painter, Cell]] = [
                                                      (
                                                       painter,
                                                       cmk.gui.plugins.views.utils.Cell(cmk.gui.views.View("", {}, {}),PainterSpec(painter.ident))
                                                      )
                                                      for painter in painters
                                                     ]

    dummy_ident: str = "einszwo"
    for painter, cell in painters_and_cells:
        cell._painter_params = {"ident": dummy_ident} # pylint: disable=protected-access
        expected_title: str = painter.ident
        if painter.ident in ["host_custom_variable", "service_custom_variable"]:
            expected_title += "_%s" % dummy_ident
        assert painter.export_title(cell) == expected_title



def test_legacy_register_painter(monkeypatch):
    monkeypatch.setattr(cmk.gui.plugins.views.utils, "painter_registry",
                        cmk.gui.plugins.views.utils.PainterRegistry())

    def rendr(row):
        return ("abc", "xyz")

    cmk.gui.plugins.views.utils.register_painter(
        "abc", {
            "title": "A B C",
            "short": "ABC",
            "columns": ["x"],
            "sorter": "aaaa",
            "options": ["opt1"],
            "printable": False,
            "paint": rendr,
            "groupby": "xyz",
        })

    painter = cmk.gui.plugins.views.utils.painter_registry["abc"]()
    dummy_cell = cmk.gui.plugins.views.utils.Cell(cmk.gui.views.View("", {}, {}), PainterSpec(painter.ident))
    assert isinstance(painter, cmk.gui.plugins.views.utils.Painter)
    assert painter.ident == "abc"
    assert painter.title(dummy_cell) == "A B C"
    assert painter.short_title(dummy_cell) == "ABC"
    assert painter.columns == ["x"]
    assert painter.sorter == "aaaa"
    assert painter.painter_options == ["opt1"]
    assert painter.printable is False
    assert painter.render(row={}, cell=dummy_cell) == ("abc", "xyz")
    assert painter.group_by(row={}, cell=dummy_cell) == "xyz"


# These tests make adding new elements needlessly painful.
# Skip pending discussion with development team.
@pytest.mark.skip
def test_registered_sorters():
    expected: Dict[str, Dict[str, Any]] = {
        'aggr_group': {
            'columns': ['aggr_group'],
            'title': u'Aggregation group'
        },
        'aggr_name': {
            'columns': ['aggr_name'],
            'title': u'Aggregation name'
        },
        'alerts_crit': {
            'columns': ['log_alerts_crit'],
            'title': u'Number of critical alerts'
        },
        'alerts_ok': {
            'columns': ['log_alerts_ok'],
            'title': u'Number of recoveries'
        },
        'alerts_problem': {
            'columns': ['log_alerts_problem'],
            'title': u'Number of problem alerts'
        },
        'alerts_unknown': {
            'columns': ['log_alerts_unknown'],
            'title': u'Number of unknown alerts'
        },
        'alerts_warn': {
            'columns': ['log_alerts_warn'],
            'title': u'Number of warnings'
        },
        'alias': {
            'columns': ['host_alias'],
            'title': u'Host alias'
        },
        'comment_author': {
            'columns': ['comment_author'],
            'title': u'Comment author'
        },
        'comment_comment': {
            'columns': ['comment_comment'],
            'title': u'Comment text'
        },
        'comment_expires': {
            'columns': ['comment_expire_time'],
            'title': u'Comment expiry time'
        },
        'comment_id': {
            'columns': ['comment_id'],
            'title': u'Comment id'
        },
        'comment_time': {
            'columns': ['comment_entry_time'],
            'title': u'Comment entry time'
        },
        'comment_type': {
            'columns': ['comment_type'],
            'title': u'Comment type'
        },
        'comment_what': {
            'columns': ['comment_type'],
            'title': u'Comment type (host/service)'
        },
        'downtime_author': {
            'columns': ['downtime_author'],
            'title': u'Downtime author'
        },
        'downtime_comment': {
            'columns': ['downtime_comment'],
            'title': u'Downtime comment'
        },
        'downtime_end_time': {
            'columns': ['downtime_end_time'],
            'title': u'Downtime end'
        },
        'downtime_entry_time': {
            'columns': ['downtime_entry_time'],
            'title': u'Downtime entry time'
        },
        'downtime_fixed': {
            'columns': ['downtime_fixed'],
            'title': u'Downtime start mode'
        },
        'downtime_id': {
            'columns': ['downtime_id'],
            'title': u'Downtime id'
        },
        'downtime_start_time': {
            'columns': ['downtime_start_time'],
            'title': u'Downtime start'
        },
        'downtime_type': {
            'columns': ['downtime_type'],
            'title': u'Downtime active or pending'
        },
        'downtime_what': {
            'columns': ['downtime_is_service'],
            'title': u'Downtime for host/service'
        },
        'event_application': {
            'columns': ['event_application'],
            'title': u'Application / Syslog-Tag'
        },
        'event_comment': {
            'columns': ['event_comment'],
            'title': u'Comment to the event'
        },
        'event_contact': {
            'columns': ['event_contact'],
            'title': u'Contact Person'
        },
        'event_count': {
            'columns': ['event_count'],
            'title': u'Count (number of recent occurrances)'
        },
        'event_facility': {
            'columns': ['event_facility'],
            'title': u'Syslog-Facility'
        },
        'event_first': {
            'columns': ['event_first'],
            'title': u'Time of first occurrence of this serial'
        },
        'event_host': {
            'columns': ['event_host', 'host_name'],
            'title': u'Hostname'
        },
        'event_id': {
            'columns': ['event_id'],
            'title': u'ID of the event'
        },
        'event_ipaddress': {
            'columns': ['event_ipaddress'],
            'title': u'Original IP-Address'
        },
        'event_last': {
            'columns': ['event_last'],
            'title': u'Time of last occurrance'
        },
        'event_owner': {
            'columns': ['event_owner'],
            'title': u'Owner of event'
        },
        'event_phase': {
            'columns': ['event_phase'],
            'title': u'Phase of event (open, counting, etc.)'
        },
        'event_pid': {
            'columns': ['event_pid'],
            'title': u'Process ID'
        },
        'event_priority': {
            'columns': ['event_priority'],
            'title': u'Syslog-Priority'
        },
        'event_rule_id': {
            'columns': ['event_rule_id'],
            'title': u'Rule-ID'
        },
        'event_sl': {
            'columns': ['event_sl'],
            'title': u'Service-Level'
        },
        'event_state': {
            'columns': ['event_state'],
            'title': u'State (severity) of event'
        },
        'event_text': {
            'columns': ['event_text'],
            'title': u'Text/Message of the event'
        },
        'hg_alias': {
            'columns': ['hostgroup_alias'],
            'title': u'Hostgroup alias'
        },
        'hg_name': {
            'columns': ['hostgroup_name'],
            'title': u'Hostgroup name'
        },
        'hg_num_hosts_down': {
            'columns': ['hostgroup_num_hosts_down'],
            'title': u'Number of hosts in state DOWN (Host Group)'
        },
        'hg_num_hosts_pending': {
            'columns': ['hostgroup_num_hosts_pending'],
            'title': u'Number of hosts in state PENDING (Host Group)'
        },
        'hg_num_hosts_unreach': {
            'columns': ['hostgroup_num_hosts_unreach'],
            'title': u'Number of hosts in state UNREACH (Host Group)'
        },
        'hg_num_hosts_up': {
            'columns': ['hostgroup_num_hosts_up'],
            'title': u'Number of hosts in state UP (Host Group)'
        },
        'hg_num_services': {
            'columns': ['hostgroup_num_services'],
            'title': u'Number of services (Host Group)'
        },
        'hg_num_services_crit': {
            'columns': ['hostgroup_num_services_crit'],
            'title': u'Number of services in state CRIT (Host Group)'
        },
        'hg_num_services_ok': {
            'columns': ['hostgroup_num_services_ok'],
            'title': u'Number of services in state OK (Host Group)'
        },
        'hg_num_services_pending': {
            'columns': ['hostgroup_num_services_pending'],
            'title': u'Number of services in state PENDING (Host Group)'
        },
        'hg_num_services_unknown': {
            'columns': ['hostgroup_num_services_unknown'],
            'title': u'Number of services in state UNKNOWN (Host Group)'
        },
        'hg_num_services_warn': {
            'columns': ['hostgroup_num_services_warn'],
            'title': u'Number of services in state WARN (Host Group)'
        },
        'history_addinfo': {
            'columns': ['history_addinfo'],
            'title': u'Additional Information'
        },
        'history_line': {
            'columns': ['history_line'],
            'title': u'Line number in log file'
        },
        'history_time': {
            'columns': ['history_time'],
            'title': u'Time of entry in logfile'
        },
        'history_what': {
            'columns': ['history_what'],
            'title': u'Type of event action'
        },
        'history_who': {
            'columns': ['history_who'],
            'title': u'User who performed action'
        },
        'host': {
            'columns': ['host_custom_variable_names', 'host_custom_variable_values'],
            'title': u'Host Tags (raw)'
        },
        'host_acknowledged': {
            'columns': ['host_acknowledged'],
            'title': u'Host problem acknowledged'
        },
        'host_address': {
            'columns': ['host_address'],
            'title': u'Host address (Primary)'
        },
        'host_address_family': {
            'columns': ['host_custom_variable_names', 'host_custom_variable_values'],
            'title': u'Host address family (Primary)'
        },
        'host_attempt': {
            'columns': ['host_current_attempt', 'host_max_check_attempts'],
            'title': u'Current host check attempt'
        },
        'host_check_age': {
            'columns': ['host_has_been_checked', 'host_last_check'],
            'title': u'The time since the last check of the host'
        },
        'host_check_command': {
            'columns': ['host_check_command'],
            'title': u'Host check command'
        },
        'host_check_duration': {
            'columns': ['host_execution_time'],
            'title': u'Host check duration'
        },
        'host_check_latency': {
            'columns': ['host_latency'],
            'title': u'Host check latency'
        },
        'host_check_type': {
            'columns': ['host_check_type'],
            'title': u'Host check type'
        },
        'host_childs': {
            'columns': ['host_childs'],
            'title': u"Host's children"
        },
        'host_contact_groups': {
            'columns': ['host_contact_groups'],
            'title': u'Host contact groups'
        },
        'host_contacts': {
            'columns': ['host_contacts'],
            'title': u'Host contacts'
        },
        'host_flapping': {
            'columns': ['host_is_flapping'],
            'title': u'Host is flapping'
        },
        'host_group_memberlist': {
            'columns': ['host_groups'],
            'title': u'Host groups the host is member of'
        },
        'host_in_downtime': {
            'columns': ['host_scheduled_downtime_depth'],
            'title': u'Host in downtime'
        },
        'host_in_notifper': {
            'columns': ['host_in_notification_period'],
            'title': u'Host in notif. period'
        },
        'host_ipv4_address': {
            'columns': ['host_custom_variable_names', 'host_custom_variable_values'],
            'title': u'Host IPv4 address'
        },
        'host_is_active': {
            'columns': ['host_active_checks_enabled'],
            'title': u'Host is active'
        },
        'host_last_notification': {
            'columns': ['host_last_notification'],
            'title': u'The time of the last host notification'
        },
        'host_name': {
            'columns': ['host_name'],
            'title': u'Host name'
        },
        'host_next_check': {
            'columns': ['host_next_check'],
            'title': u'The time of the next scheduled host check'
        },
        'host_next_notification': {
            'columns': ['host_next_notification'],
            'title': u'The time of the next host notification'
        },
        'host_notifper': {
            'columns': ['host_notification_period'],
            'title': u'Host notification period'
        },
        'host_parents': {
            'columns': ['host_parents'],
            'title': u"Host's parents"
        },
        'host_perf_data': {
            'columns': ['host_perf_data'],
            'title': u'Host performance data'
        },
        'host_plugin_output': {
            'columns': ['host_plugin_output', 'host_custom_variables'],
            'title': u'Output of host check plugin'
        },
        'host_servicelevel': {
            'columns': ['host_custom_variable_names', 'host_custom_variable_values'],
            'title': u'Host service level'
        },
        'host_state_age': {
            'columns': ['host_has_been_checked', 'host_last_state_change'],
            'title': u'The age of the current host state'
        },
        'host_tag_address_family': {
            'columns': ['host_custom_variable_names', 'host_custom_variable_values'],
            'title': u'Host tag: Address/IP Address Family '
        },
        'host_tag_agent': {
            'columns': ['host_custom_variable_names', 'host_custom_variable_values'],
            'title': u'Host tag: Data sources/Check_MK Agent'
        },
        'host_tag_snmp': {
            'columns': ['host_custom_variable_names', 'host_custom_variable_values'],
            'title': u'Host tag: Data sources/SNMP'
        },
        'hostgroup': {
            'columns': ['hostgroup_alias'],
            'title': u'Hostgroup'
        },
        'hoststate': {
            'columns': ['host_state', 'host_has_been_checked'],
            'title': u'Host state'
        },
        'inv_hardware_cpu_arch': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'title': u'Inventory: Processor \u27a4 CPU Architecture'
        },
        'inv_hardware_cpu_bus_speed': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'title': u'Inventory: Processor \u27a4 Bus Speed'
        },
        'inv_hardware_cpu_cache_size': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'title': u'Inventory: Processor \u27a4 Cache Size'
        },
        'inv_hardware_cpu_cores': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'title': u'Inventory: Processor \u27a4 Total Number of Cores'
        },
        'inv_hardware_cpu_cores_per_cpu': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'title': u'Inventory: Processor \u27a4 Cores per CPU'
        },
        'inv_hardware_cpu_cpus': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'title': u'Inventory: Processor \u27a4 Number of physical CPUs'
        },
        'inv_hardware_cpu_entitlement': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'title': u'Inventory: Processor \u27a4 CPU Entitlement'
        },
        'inv_hardware_cpu_logical_cpus': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'title': u'Inventory: Processor \u27a4 Number of logical CPUs'
        },
        'inv_hardware_cpu_max_speed': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'title': u'Inventory: Processor \u27a4 Maximum Speed'
        },
        'inv_hardware_cpu_model': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'title': u'Inventory: Processor \u27a4 Model'
        },
        'inv_hardware_cpu_sharing_mode': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'title': u'Inventory: Processor \u27a4 CPU sharing mode'
        },
        'inv_hardware_cpu_smt_threads': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'title': u'Inventory: Processor \u27a4 Simultaneous multithreading'
        },
        'inv_hardware_cpu_threads': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'title': u'Inventory: Processor \u27a4 Total Number of Hyperthreads'
        },
        'inv_hardware_cpu_threads_per_cpu': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'title': u'Inventory: Processor \u27a4 Hyperthreads per CPU'
        },
        'inv_hardware_cpu_voltage': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'title': u'Inventory: Processor \u27a4 Voltage'
        },
        'inv_hardware_memory_total_ram_usable': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'title': u'Inventory: Memory (RAM) \u27a4 Total usable RAM'
        },
        'inv_hardware_memory_total_swap': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'title': u'Inventory: Memory (RAM) \u27a4 Total swap space'
        },
        'inv_hardware_memory_total_vmalloc': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'title': u'Inventory: Memory (RAM) \u27a4 Virtual addresses for mapping'
        },
        'inv_hardware_storage_controller_version': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'title': u'Inventory: Controller \u27a4 Version'
        },
        'inv_hardware_system_expresscode': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'title': u'Inventory: System \u27a4 Express Servicecode'
        },
        'inv_hardware_system_manufacturer': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'title': u'Inventory: System \u27a4 Manufacturer'
        },
        'inv_hardware_system_model': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'title': u'Inventory: System \u27a4 Model Name'
        },
        'inv_hardware_system_model_name': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'title': u"Inventory: System \u27a4 Model Name - LEGACY, don't use"
        },
        'inv_hardware_system_product': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'title': u'Inventory: System \u27a4 Product'
        },
        'inv_hardware_system_serial': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'title': u'Inventory: System \u27a4 Serial Number'
        },
        'inv_hardware_system_serial_number': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'title': u"Inventory: System \u27a4 Serial Number - LEGACY, don't use"
        },
        'inv_networking_available_ethernet_ports': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'title': u'Inventory: Networking \u27a4 Ports available'
        },
        'inv_networking_total_ethernet_ports': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'title': u'Inventory: Networking \u27a4 Ports'
        },
        'inv_networking_total_interfaces': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'title': u'Inventory: Networking \u27a4 Interfaces'
        },
        'inv_networking_wlan': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'title': u'Inventory: Networking \u27a4 WLAN'
        },
        'inv_networking_wlan_controller': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'title': u'Inventory: WLAN \u27a4 Controller'
        },
        'inv_software_applications_check_mk_cluster_is_cluster': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'title': u'Inventory: Cluster \u27a4 Cluster host'
        },
        'inv_software_applications_citrix_controller_controller_version': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'title': u'Inventory: Controller \u27a4 Controller Version'
        },
        'inv_software_applications_citrix_vm_agent_version': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'title': u'Inventory: Virtual Machine \u27a4 Agent Version'
        },
        'inv_software_applications_citrix_vm_catalog': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'title': u'Inventory: Virtual Machine \u27a4 Catalog'
        },
        'inv_software_applications_citrix_vm_desktop_group_name': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'title': u'Inventory: Virtual Machine \u27a4 Desktop Group Name'
        },
        'inv_software_applications_docker_container_node_name': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'title': u'Inventory: Container \u27a4 Node name'
        },
        'inv_software_applications_docker_num_containers_paused': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'title': u'Inventory: Docker \u27a4 # Containers paused'
        },
        'inv_software_applications_docker_num_containers_running': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'title': u'Inventory: Docker \u27a4 # Containers running'
        },
        'inv_software_applications_docker_num_containers_stopped': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'title': u'Inventory: Docker \u27a4 # Containers stopped'
        },
        'inv_software_applications_docker_num_containers_total': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'title': u'Inventory: Docker \u27a4 # Containers'
        },
        'inv_software_applications_docker_num_images': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'title': u'Inventory: Docker \u27a4 # Images'
        },
        'inv_software_bios_date': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'title': u'Inventory: BIOS \u27a4 Date'
        },
        'inv_software_bios_vendor': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'title': u'Inventory: BIOS \u27a4 Vendor'
        },
        'inv_software_bios_version': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'title': u'Inventory: BIOS \u27a4 Version'
        },
        'inv_software_configuration_snmp_info_contact': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'title': u'Inventory: SNMP Information \u27a4 Contact'
        },
        'inv_software_configuration_snmp_info_location': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'title': u'Inventory: SNMP Information \u27a4 Location'
        },
        'inv_software_configuration_snmp_info_name': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'title': u'Inventory: SNMP Information \u27a4 System name'
        },
        'inv_software_firmware_platform_level': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'title': u'Inventory: Firmware \u27a4 Platform Firmware level'
        },
        'inv_software_firmware_vendor': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'title': u'Inventory: Firmware \u27a4 Vendor'
        },
        'inv_software_firmware_version': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'title': u'Inventory: Firmware \u27a4 Version'
        },
        'inv_software_os_arch': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'title': u'Inventory: Operating System \u27a4 Kernel Architecture'
        },
        'inv_software_os_install_date': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'title': u'Inventory: Operating System \u27a4 Install Date'
        },
        'inv_software_os_kernel_version': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'title': u'Inventory: Operating System \u27a4 Kernel Version'
        },
        'inv_software_os_name': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'title': u'Inventory: Operating System \u27a4 Name'
        },
        'inv_software_os_service_pack': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'title': u'Inventory: Operating System \u27a4 Latest Service Pack'
        },
        'inv_software_os_type': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'title': u'Inventory: Operating System \u27a4 Type'
        },
        'inv_software_os_vendor': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'title': u'Inventory: Operating System \u27a4 Vendor'
        },
        'inv_software_os_version': {
            'columns': ['host_inventory', 'host_structured_status'],
            'load_inv': True,
            'title': u'Inventory: Operating System \u27a4 Version'
        },
        'invbackplane_description': {
            'columns': ['invbackplane_description'],
            'title': u'Inventory: Description'
        },
        'invbackplane_index': {
            'columns': ['invbackplane_index'],
            'title': u'Inventory: Index'
        },
        'invbackplane_location': {
            'columns': ['invbackplane_location'],
            'title': u'Inventory: Location'
        },
        'invbackplane_manufacturer': {
            'columns': ['invbackplane_manufacturer'],
            'title': u'Inventory: Manufacturer'
        },
        'invbackplane_model': {
            'columns': ['invbackplane_model'],
            'title': u'Inventory: Model Name'
        },
        'invbackplane_name': {
            'columns': ['invbackplane_name'],
            'title': u'Inventory: Name'
        },
        'invbackplane_serial': {
            'columns': ['invbackplane_serial'],
            'title': u'Inventory: Serial Number'
        },
        'invbackplane_software': {
            'columns': ['invbackplane_software'],
            'title': u'Inventory: Software'
        },
        'invchassis_description': {
            'columns': ['invchassis_description'],
            'title': u'Inventory: Description'
        },
        'invchassis_index': {
            'columns': ['invchassis_index'],
            'title': u'Inventory: Index'
        },
        'invchassis_location': {
            'columns': ['invchassis_location'],
            'title': u'Inventory: Location'
        },
        'invchassis_manufacturer': {
            'columns': ['invchassis_manufacturer'],
            'title': u'Inventory: Manufacturer'
        },
        'invchassis_model': {
            'columns': ['invchassis_model'],
            'title': u'Inventory: Model Name'
        },
        'invchassis_name': {
            'columns': ['invchassis_name'],
            'title': u'Inventory: Name'
        },
        'invchassis_serial': {
            'columns': ['invchassis_serial'],
            'title': u'Inventory: Serial Number'
        },
        'invchassis_software': {
            'columns': ['invchassis_software'],
            'title': u'Inventory: Software'
        },
        'invcontainer_description': {
            'columns': ['invcontainer_description'],
            'title': u'Inventory: Description'
        },
        'invcontainer_index': {
            'columns': ['invcontainer_index'],
            'title': u'Inventory: Index'
        },
        'invcontainer_location': {
            'columns': ['invcontainer_location'],
            'title': u'Inventory: Location'
        },
        'invcontainer_manufacturer': {
            'columns': ['invcontainer_manufacturer'],
            'title': u'Inventory: Manufacturer'
        },
        'invcontainer_model': {
            'columns': ['invcontainer_model'],
            'title': u'Inventory: Model Name'
        },
        'invcontainer_name': {
            'columns': ['invcontainer_name'],
            'title': u'Inventory: Name'
        },
        'invcontainer_serial': {
            'columns': ['invcontainer_serial'],
            'title': u'Inventory: Serial Number'
        },
        'invcontainer_software': {
            'columns': ['invcontainer_software'],
            'title': u'Inventory: Software'
        },
        'invdockercontainers_creation': {
            'columns': ['invdockercontainers_creation'],
            'title': u'Inventory: Creation'
        },
        'invdockercontainers_id': {
            'columns': ['invdockercontainers_id'],
            'title': u'Inventory: ID'
        },
        'invdockercontainers_labels': {
            'columns': ['invdockercontainers_labels'],
            'title': u'Inventory: Labels'
        },
        'invdockercontainers_name': {
            'columns': ['invdockercontainers_name'],
            'title': u'Inventory: Name'
        },
        'invdockercontainers_repository': {
            'columns': ['invdockercontainers_repository'],
            'title': u'Inventory: Repository'
        },
        'invdockercontainers_status': {
            'columns': ['invdockercontainers_status'],
            'title': u'Inventory: Status'
        },
        'invdockercontainers_tag': {
            'columns': ['invdockercontainers_tag'],
            'title': u'Inventory: Tag'
        },
        'invdockerimages_amount_containers': {
            'columns': ['invdockerimages_amount_containers'],
            'title': u'Inventory: # Containers'
        },
        'invdockerimages_creation': {
            'columns': ['invdockerimages_creation'],
            'title': u'Inventory: Creation'
        },
        'invdockerimages_id': {
            'columns': ['invdockerimages_id'],
            'title': u'Inventory: ID'
        },
        'invdockerimages_labels': {
            'columns': ['invdockerimages_labels'],
            'title': u'Inventory: Labels'
        },
        'invdockerimages_repository': {
            'columns': ['invdockerimages_repository'],
            'title': u'Inventory: Repository'
        },
        'invdockerimages_size': {
            'columns': ['invdockerimages_size'],
            'title': u'Inventory: Size'
        },
        'invdockerimages_tag': {
            'columns': ['invdockerimages_tag'],
            'title': u'Inventory: Tag'
        },
        'invfan_description': {
            'columns': ['invfan_description'],
            'title': u'Inventory: Description'
        },
        'invfan_index': {
            'columns': ['invfan_index'],
            'title': u'Inventory: Index'
        },
        'invfan_location': {
            'columns': ['invfan_location'],
            'title': u'Inventory: Location'
        },
        'invfan_manufacturer': {
            'columns': ['invfan_manufacturer'],
            'title': u'Inventory: Manufacturer'
        },
        'invfan_model': {
            'columns': ['invfan_model'],
            'title': u'Inventory: Model Name'
        },
        'invfan_name': {
            'columns': ['invfan_name'],
            'title': u'Inventory: Name'
        },
        'invfan_serial': {
            'columns': ['invfan_serial'],
            'title': u'Inventory: Serial Number'
        },
        'invfan_software': {
            'columns': ['invfan_software'],
            'title': u'Inventory: Software'
        },
        'invhist_changed': {
            'columns': ['invhist_changed'],
            'title': u'changed entries'
        },
        'invhist_new': {
            'columns': ['invhist_new'],
            'title': u'new entries'
        },
        'invhist_removed': {
            'columns': ['invhist_removed'],
            'title': u'Removed entries'
        },
        'invhist_time': {
            'columns': ['invhist_time'],
            'title': u'Inventory Date/Time'
        },
        'invinterface_admin_status': {
            'columns': ['invinterface_admin_status'],
            'title': u'Inventory: Administrative Status'
        },
        'invinterface_alias': {
            'columns': ['invinterface_alias'],
            'title': u'Inventory: Alias'
        },
        'invinterface_available': {
            'columns': ['invinterface_available'],
            'title': u'Inventory: Port Usage'
        },
        'invinterface_description': {
            'columns': ['invinterface_description'],
            'title': u'Inventory: Description'
        },
        'invinterface_index': {
            'columns': ['invinterface_index'],
            'title': u'Inventory: Index'
        },
        'invinterface_last_change': {
            'columns': ['invinterface_last_change'],
            'title': u'Inventory: Last Change'
        },
        'invinterface_oper_status': {
            'columns': ['invinterface_oper_status'],
            'title': u'Inventory: Operational Status'
        },
        'invinterface_phys_address': {
            'columns': ['invinterface_phys_address'],
            'title': u'Inventory: Physical Address (MAC)'
        },
        'invinterface_port_type': {
            'columns': ['invinterface_port_type'],
            'title': u'Inventory: Type'
        },
        'invinterface_speed': {
            'columns': ['invinterface_speed'],
            'title': u'Inventory: Speed'
        },
        'invinterface_vlans': {
            'columns': ['invinterface_vlans'],
            'title': u'Inventory: VLANs'
        },
        'invinterface_vlantype': {
            'columns': ['invinterface_vlantype'],
            'title': u'Inventory: VLAN type'
        },
        'invmodule_bootloader': {
            'columns': ['invmodule_bootloader'],
            'title': u'Inventory: Bootloader'
        },
        'invmodule_description': {
            'columns': ['invmodule_description'],
            'title': u'Inventory: Description'
        },
        'invmodule_firmware': {
            'columns': ['invmodule_firmware'],
            'title': u'Inventory: Firmware'
        },
        'invmodule_index': {
            'columns': ['invmodule_index'],
            'title': u'Inventory: Index'
        },
        'invmodule_location': {
            'columns': ['invmodule_location'],
            'title': u'Inventory: Location'
        },
        'invmodule_manufacturer': {
            'columns': ['invmodule_manufacturer'],
            'title': u'Inventory: Manufacturer'
        },
        'invmodule_model': {
            'columns': ['invmodule_model'],
            'title': u'Inventory: Model Name'
        },
        'invmodule_name': {
            'columns': ['invmodule_name'],
            'title': u'Inventory: Name'
        },
        'invmodule_serial': {
            'columns': ['invmodule_serial'],
            'title': u'Inventory: Serial Number'
        },
        'invmodule_software': {
            'columns': ['invmodule_software'],
            'title': u'Inventory: Software'
        },
        'invmodule_type': {
            'columns': ['invmodule_type'],
            'title': u'Inventory: Type'
        },
        'invoradataguardstats_db_unique': {
            'columns': ['invoradataguardstats_db_unique'],
            'title': u'Inventory: Name'
        },
        'invoradataguardstats_role': {
            'columns': ['invoradataguardstats_role'],
            'title': u'Inventory: Role'
        },
        'invoradataguardstats_sid': {
            'columns': ['invoradataguardstats_sid'],
            'title': u'Inventory: SID'
        },
        'invoradataguardstats_switchover': {
            'columns': ['invoradataguardstats_switchover'],
            'title': u'Inventory: Switchover'
        },
        'invorainstance_db_creation_time': {
            'columns': ['invorainstance_db_creation_time'],
            'title': u'Inventory: Creation time'
        },
        'invorainstance_db_uptime': {
            'columns': ['invorainstance_db_uptime'],
            'title': u'Inventory: Uptime'
        },
        'invorainstance_logins': {
            'columns': ['invorainstance_logins'],
            'title': u'Inventory: Logins'
        },
        'invorainstance_logmode': {
            'columns': ['invorainstance_logmode'],
            'title': u'Inventory: Log mode'
        },
        'invorainstance_openmode': {
            'columns': ['invorainstance_openmode'],
            'title': u'Inventory: Open mode'
        },
        'invorainstance_sid': {
            'columns': ['invorainstance_sid'],
            'title': u'Inventory: SID'
        },
        'invorainstance_version': {
            'columns': ['invorainstance_version'],
            'title': u'Inventory: Version'
        },
        'invorarecoveryarea_flashback': {
            'columns': ['invorarecoveryarea_flashback'],
            'title': u'Inventory: Flashback'
        },
        'invorarecoveryarea_sid': {
            'columns': ['invorarecoveryarea_sid'],
            'title': u'Inventory: SID'
        },
        'invorasga_buf_cache_size': {
            'columns': ['invorasga_buf_cache_size'],
            'title': u'Inventory: Buffer cache size'
        },
        'invorasga_data_trans_cache_size': {
            'columns': ['invorasga_data_trans_cache_size'],
            'title': u'Inventory: Data transfer cache size'
        },
        'invorasga_fixed_size': {
            'columns': ['invorasga_fixed_size'],
            'title': u'Inventory: Fixed size'
        },
        'invorasga_free_mem_avail': {
            'columns': ['invorasga_free_mem_avail'],
            'title': u'Inventory: Free SGA memory available'
        },
        'invorasga_granule_size': {
            'columns': ['invorasga_granule_size'],
            'title': u'Inventory: Granule size'
        },
        'invorasga_in_mem_area_size': {
            'columns': ['invorasga_in_mem_area_size'],
            'title': u'Inventory: In-memory area'
        },
        'invorasga_java_pool_size': {
            'columns': ['invorasga_java_pool_size'],
            'title': u'Inventory: Java pool size'
        },
        'invorasga_large_pool_size': {
            'columns': ['invorasga_large_pool_size'],
            'title': u'Inventory: Large pool size'
        },
        'invorasga_max_size': {
            'columns': ['invorasga_max_size'],
            'title': u'Inventory: Maximum size'
        },
        'invorasga_redo_buffer': {
            'columns': ['invorasga_redo_buffer'],
            'title': u'Inventory: Redo buffers'
        },
        'invorasga_shared_io_pool_size': {
            'columns': ['invorasga_shared_io_pool_size'],
            'title': u'Inventory: Shared pool size'
        },
        'invorasga_shared_pool_size': {
            'columns': ['invorasga_shared_pool_size'],
            'title': u'Inventory: Shared pool size'
        },
        'invorasga_sid': {
            'columns': ['invorasga_sid'],
            'title': u'Inventory: SID'
        },
        'invorasga_start_oh_shared_pool': {
            'columns': ['invorasga_start_oh_shared_pool'],
            'title': u'Inventory: Startup overhead in shared pool'
        },
        'invorasga_streams_pool_size': {
            'columns': ['invorasga_streams_pool_size'],
            'title': u'Inventory: Streams pool size'
        },
        'invoratablespace_autoextensible': {
            'columns': ['invoratablespace_autoextensible'],
            'title': u'Inventory: Autoextensible'
        },
        'invoratablespace_current_size': {
            'columns': ['invoratablespace_current_size'],
            'title': u'Inventory: Current size'
        },
        'invoratablespace_free_space': {
            'columns': ['invoratablespace_free_space'],
            'title': u'Inventory: Free space'
        },
        'invoratablespace_increment_size': {
            'columns': ['invoratablespace_increment_size'],
            'title': u'Inventory: Increment size'
        },
        'invoratablespace_max_size': {
            'columns': ['invoratablespace_max_size'],
            'title': u'Inventory: Max. size'
        },
        'invoratablespace_name': {
            'columns': ['invoratablespace_name'],
            'title': u'Inventory: Name'
        },
        'invoratablespace_num_increments': {
            'columns': ['invoratablespace_num_increments'],
            'title': u'Inventory: Number of increments'
        },
        'invoratablespace_sid': {
            'columns': ['invoratablespace_sid'],
            'title': u'Inventory: SID'
        },
        'invoratablespace_type': {
            'columns': ['invoratablespace_type'],
            'title': u'Inventory: Type'
        },
        'invoratablespace_used_size': {
            'columns': ['invoratablespace_used_size'],
            'title': u'Inventory: Used size'
        },
        'invoratablespace_version': {
            'columns': ['invoratablespace_version'],
            'title': u'Inventory: Version'
        },
        'invother_description': {
            'columns': ['invother_description'],
            'title': u'Inventory: Description'
        },
        'invother_index': {
            'columns': ['invother_index'],
            'title': u'Inventory: Index'
        },
        'invother_location': {
            'columns': ['invother_location'],
            'title': u'Inventory: Location'
        },
        'invother_manufacturer': {
            'columns': ['invother_manufacturer'],
            'title': u'Inventory: Manufacturer'
        },
        'invother_model': {
            'columns': ['invother_model'],
            'title': u'Inventory: Model Name'
        },
        'invother_name': {
            'columns': ['invother_name'],
            'title': u'Inventory: Name'
        },
        'invother_serial': {
            'columns': ['invother_serial'],
            'title': u'Inventory: Serial Number'
        },
        'invother_software': {
            'columns': ['invother_software'],
            'title': u'Inventory: Software'
        },
        'invpsu_description': {
            'columns': ['invpsu_description'],
            'title': u'Inventory: Description'
        },
        'invpsu_index': {
            'columns': ['invpsu_index'],
            'title': u'Inventory: Index'
        },
        'invpsu_location': {
            'columns': ['invpsu_location'],
            'title': u'Inventory: Location'
        },
        'invpsu_manufacturer': {
            'columns': ['invpsu_manufacturer'],
            'title': u'Inventory: Manufacturer'
        },
        'invpsu_model': {
            'columns': ['invpsu_model'],
            'title': u'Inventory: Model Name'
        },
        'invpsu_name': {
            'columns': ['invpsu_name'],
            'title': u'Inventory: Name'
        },
        'invpsu_serial': {
            'columns': ['invpsu_serial'],
            'title': u'Inventory: Serial Number'
        },
        'invpsu_software': {
            'columns': ['invpsu_software'],
            'title': u'Inventory: Software'
        },
        'invsensor_description': {
            'columns': ['invsensor_description'],
            'title': u'Inventory: Description'
        },
        'invsensor_index': {
            'columns': ['invsensor_index'],
            'title': u'Inventory: Index'
        },
        'invsensor_location': {
            'columns': ['invsensor_location'],
            'title': u'Inventory: Location'
        },
        'invsensor_manufacturer': {
            'columns': ['invsensor_manufacturer'],
            'title': u'Inventory: Manufacturer'
        },
        'invsensor_model': {
            'columns': ['invsensor_model'],
            'title': u'Inventory: Model Name'
        },
        'invsensor_name': {
            'columns': ['invsensor_name'],
            'title': u'Inventory: Name'
        },
        'invsensor_serial': {
            'columns': ['invsensor_serial'],
            'title': u'Inventory: Serial Number'
        },
        'invsensor_software': {
            'columns': ['invsensor_software'],
            'title': u'Inventory: Software'
        },
        'invstack_description': {
            'columns': ['invstack_description'],
            'title': u'Inventory: Description'
        },
        'invstack_index': {
            'columns': ['invstack_index'],
            'title': u'Inventory: Index'
        },
        'invstack_location': {
            'columns': ['invstack_location'],
            'title': u'Inventory: Location'
        },
        'invstack_manufacturer': {
            'columns': ['invstack_manufacturer'],
            'title': u'Inventory: Manufacturer'
        },
        'invstack_model': {
            'columns': ['invstack_model'],
            'title': u'Inventory: Model Name'
        },
        'invstack_name': {
            'columns': ['invstack_name'],
            'title': u'Inventory: Name'
        },
        'invstack_serial': {
            'columns': ['invstack_serial'],
            'title': u'Inventory: Serial Number'
        },
        'invstack_software': {
            'columns': ['invstack_software'],
            'title': u'Inventory: Software'
        },
        'invswpac_arch': {
            'columns': ['invswpac_arch'],
            'title': u'Inventory: Architecture'
        },
        'invswpac_install_date': {
            'columns': ['invswpac_install_date'],
            'title': u'Inventory: Install Date'
        },
        'invswpac_name': {
            'columns': ['invswpac_name'],
            'title': u'Inventory: Name'
        },
        'invswpac_package_type': {
            'columns': ['invswpac_package_type'],
            'title': u'Inventory: Type'
        },
        'invswpac_package_version': {
            'columns': ['invswpac_package_version'],
            'title': u'Inventory: Package Version'
        },
        'invswpac_path': {
            'columns': ['invswpac_path'],
            'title': u'Inventory: Path'
        },
        'invswpac_size': {
            'columns': ['invswpac_size'],
            'title': u'Inventory: Size'
        },
        'invswpac_summary': {
            'columns': ['invswpac_summary'],
            'title': u'Inventory: Description'
        },
        'invswpac_vendor': {
            'columns': ['invswpac_vendor'],
            'title': u'Inventory: Publisher'
        },
        'invswpac_version': {
            'columns': ['invswpac_version'],
            'title': u'Inventory: Version'
        },
        'invunknown_description': {
            'columns': ['invunknown_description'],
            'title': u'Inventory: Description'
        },
        'invunknown_index': {
            'columns': ['invunknown_index'],
            'title': u'Inventory: Index'
        },
        'invunknown_location': {
            'columns': ['invunknown_location'],
            'title': u'Inventory: Location'
        },
        'invunknown_manufacturer': {
            'columns': ['invunknown_manufacturer'],
            'title': u'Inventory: Manufacturer'
        },
        'invunknown_model': {
            'columns': ['invunknown_model'],
            'title': u'Inventory: Model Name'
        },
        'invunknown_name': {
            'columns': ['invunknown_name'],
            'title': u'Inventory: Name'
        },
        'invunknown_serial': {
            'columns': ['invunknown_serial'],
            'title': u'Inventory: Serial Number'
        },
        'invunknown_software': {
            'columns': ['invunknown_software'],
            'title': u'Inventory: Software'
        },
        'log_attempt': {
            'columns': ['log_attempt'],
            'title': u'Log: number of check attempt'
        },
        'log_contact_name': {
            'columns': ['log_contact_name'],
            'title': u'Log: contact name'
        },
        'log_date': {
            'columns': ['log_time'],
            'title': u'Log: day of entry'
        },
        'log_lineno': {
            'columns': ['log_lineno'],
            'title': u'Log: line number in log file'
        },
        'log_plugin_output': {
            'columns': [
                'log_plugin_output', 'log_type', 'log_state_type', 'log_comment', 'custom_variables'
            ],
            'title': u'Log: Output'
        },
        'log_state_type': {
            'columns': ['log_state_type'],
            'title': u'Log: type of state (hard/soft/stopped/started)'
        },
        'log_time': {
            'columns': ['log_time'],
            'title': u'Log: entry time'
        },
        'log_type': {
            'columns': ['log_type'],
            'title': u'Log: event'
        },
        'log_what': {
            'columns': ['log_type'],
            'title': u'Log: host or service'
        },
        'num_problems': {
            'columns': ['host_num_services', 'host_num_services_ok', 'host_num_services_pending'],
            'title': u'Number of problems'
        },
        'num_services': {
            'columns': ['host_num_services'],
            'title': u'Number of services'
        },
        'num_services_crit': {
            'columns': ['host_num_services_crit'],
            'title': u'Number of services in state CRIT'
        },
        'num_services_ok': {
            'columns': ['host_num_services_ok'],
            'title': u'Number of services in state OK'
        },
        'num_services_pending': {
            'columns': ['host_num_services_pending'],
            'title': u'Number of services in state PENDING'
        },
        'num_services_unknown': {
            'columns': ['host_num_services_unknown'],
            'title': u'Number of services in state UNKNOWN'
        },
        'num_services_warn': {
            'columns': ['host_num_services_warn'],
            'title': u'Number of services in state WARN'
        },
        'perfometer': {
            'columns': [
                'service_perf_data', 'service_state', 'service_check_command',
                'service_pnpgraph_present', 'service_plugin_output'
            ],
            'title': u'Perf-O-Meter'
        },
        'servicegroup': {
            'columns': ['servicegroup_alias'],
            'title': u'Servicegroup'
        },
        'servicelevel': {
            'columns': ['custom_variable_names', 'custom_variable_values'],
            'title': u'Servicelevel'
        },
        'sg_alias': {
            'columns': ['servicegroup_alias'],
            'title': u'Servicegroup alias'
        },
        'sg_name': {
            'columns': ['servicegroup_name'],
            'title': u'Servicegroup name'
        },
        'sg_num_services': {
            'columns': ['servicegroup_num_services'],
            'title': u'Number of services (Service Group)'
        },
        'sg_num_services_crit': {
            'columns': ['servicegroup_num_services_crit'],
            'title': u'Number of services in state CRIT (Service Group)'
        },
        'sg_num_services_ok': {
            'columns': ['servicegroup_num_services_ok'],
            'title': u'Number of services in state OK (Service Group)'
        },
        'sg_num_services_pending': {
            'columns': ['servicegroup_num_services_pending'],
            'title': u'Number of services in state PENDING (Service Group)'
        },
        'sg_num_services_unknown': {
            'columns': ['servicegroup_num_services_unknown'],
            'title': u'Number of services in state UNKNOWN (Service Group)'
        },
        'sg_num_services_warn': {
            'columns': ['servicegroup_num_services_warn'],
            'title': u'Number of services in state WARN (Service Group)'
        },
        'site': {
            'columns': ['site'],
            'title': u'Site'
        },
        'site_host': {
            'columns': ['site', 'host_name'],
            'title': u'Host site and name'
        },
        'sitealias': {
            'columns': ['site'],
            'title': u'Site Alias'
        },
        'stateage': {
            'columns': ['service_last_state_change'],
            'title': u'Service state age'
        },
        'svc_acknowledged': {
            'columns': ['service_acknowledged'],
            'title': u'Service problem acknowledged'
        },
        'svc_attempt': {
            'columns': ['service_current_attempt', 'service_max_check_attempts'],
            'title': u'Current check attempt'
        },
        'svc_check_age': {
            'columns': ['service_has_been_checked', 'service_last_check', 'service_cached_at'],
            'title': u'The time since the last check of the service'
        },
        'svc_check_command': {
            'columns': ['service_check_command'],
            'title': u'Service check command'
        },
        'svc_check_duration': {
            'columns': ['service_execution_time'],
            'title': u'Service check duration'
        },
        'svc_check_latency': {
            'columns': ['service_latency'],
            'title': u'Service check latency'
        },
        'svc_check_type': {
            'columns': ['service_check_type'],
            'title': u'Service check type'
        },
        'svc_contact_groups': {
            'columns': ['service_contact_groups'],
            'title': u'Service contact groups'
        },
        'svc_contacts': {
            'columns': ['service_contacts'],
            'title': u'Service contacts'
        },
        'svc_flapping': {
            'columns': ['service_is_flapping'],
            'title': u'Service is flapping'
        },
        'svc_group_memberlist': {
            'columns': ['service_groups'],
            'title': u'Service groups the service is member of'
        },
        'svc_in_downtime': {
            'columns': ['service_scheduled_downtime_depth'],
            'title': u'Currently in downtime'
        },
        'svc_in_notifper': {
            'columns': ['service_in_notification_period'],
            'title': u'In notification period'
        },
        'svc_is_active': {
            'columns': ['service_active_checks_enabled'],
            'title': u'Service is active'
        },
        'svc_last_notification': {
            'columns': ['service_last_notification'],
            'title': u'The time of the last service notification'
        },
        'svc_long_plugin_output': {
            'columns': ['service_long_plugin_output'],
            'title': u'Long output of check plugin'
        },
        'svc_next_check': {
            'columns': ['service_next_check'],
            'title': u'The time of the next scheduled service check'
        },
        'svc_next_notification': {
            'columns': ['service_next_notification'],
            'title': u'The time of the next service notification'
        },
        'svc_notifications_enabled': {
            'columns': ['service_notifications_enabled'],
            'title': u'Service notifications enabled'
        },
        'svc_notifper': {
            'columns': ['service_notification_period'],
            'title': u'Service notification period'
        },
        'svc_perf_val01': {
            'columns': ['service_perf_data'],
            'title': u'Service performance data - value number 01'
        },
        'svc_perf_val02': {
            'columns': ['service_perf_data'],
            'title': u'Service performance data - value number 02'
        },
        'svc_perf_val03': {
            'columns': ['service_perf_data'],
            'title': u'Service performance data - value number 03'
        },
        'svc_perf_val04': {
            'columns': ['service_perf_data'],
            'title': u'Service performance data - value number 04'
        },
        'svc_perf_val05': {
            'columns': ['service_perf_data'],
            'title': u'Service performance data - value number 05'
        },
        'svc_perf_val06': {
            'columns': ['service_perf_data'],
            'title': u'Service performance data - value number 06'
        },
        'svc_perf_val07': {
            'columns': ['service_perf_data'],
            'title': u'Service performance data - value number 07'
        },
        'svc_perf_val08': {
            'columns': ['service_perf_data'],
            'title': u'Service performance data - value number 08'
        },
        'svc_perf_val09': {
            'columns': ['service_perf_data'],
            'title': u'Service performance data - value number 09'
        },
        'svc_perf_val10': {
            'columns': ['service_perf_data'],
            'title': u'Service performance data - value number 10'
        },
        'svc_servicelevel': {
            'columns': ['service_custom_variable_names', 'service_custom_variable_values'],
            'title': u'Service service level'
        },
        'svc_staleness': {
            'columns': ['service_staleness'],
            'title': u'Service staleness value'
        },
        'svcdescr': {
            'columns': ['service_description'],
            'title': u'Service description'
        },
        'svcdispname': {
            'columns': ['service_display_name'],
            'title': u'Service alternative display name'
        },
        'svcoutput': {
            'columns': ['service_plugin_output'],
            'title': u'Service plugin output'
        },
        'svcstate': {
            'columns': ['service_state', 'service_has_been_checked'],
            'title': u'Service state'
        },
        'wato_folder_abs': {
            'columns': ['host_filename'],
            'title': u'WATO folder - complete path'
        },
        'wato_folder_plain': {
            'columns': ['host_filename'],
            'title': u'WATO folder - just folder name'
        },
        'wato_folder_rel': {
            'columns': ['host_filename'],
            'title': u'WATO folder - relative path'
        },
    }

    for sorter_class in cmk.gui.plugins.views.sorter_registry.values():
        sorter = sorter_class()
        spec = expected[sorter.ident]

        if isinstance(spec["title"], tuple) and spec["title"][0] == "func":
            assert hasattr(sorter.title, '__call__')
        else:
            assert sorter.title == spec["title"]

        if isinstance(spec["columns"], tuple) and spec["columns"][0] == "func":
            assert hasattr(sorter.columns, '__call__')
        else:
            assert sorter.columns == spec["columns"]

        assert sorter.load_inv == spec.get("load_inv", False)


def test_register_sorter(monkeypatch):
    monkeypatch.setattr(cmk.gui.plugins.views.utils, "sorter_registry",
                        cmk.gui.plugins.views.utils.SorterRegistry())

    def cmpfunc():
        pass

    cmk.gui.plugins.views.utils.register_sorter("abc", {
        "title": "A B C",
        "columns": ["x"],
        "cmp": cmpfunc,
    })

    sorter = cmk.gui.plugins.views.utils.sorter_registry["abc"]()
    assert isinstance(sorter, cmk.gui.plugins.views.utils.Sorter)
    assert sorter.ident == "abc"
    assert sorter.title == "A B C"
    assert sorter.columns == ["x"]
    assert sorter.cmp.__name__ == cmpfunc.__name__


def test_get_needed_regular_columns(view):
    class SomeFilter(Filter):
        def display(self):
            return

        def columns_for_filter_table(self, context):
            return ["some_column"]

    columns = cmk.gui.views._get_needed_regular_columns(
        [
            SomeFilter(
                ident="some_filter",
                title="Some filter",
                sort_index=1,
                info="info",
                htmlvars=[],
                link_columns=[],
            )
        ],
        view,
    )
    assert sorted(columns) == sorted([
        'host_accept_passive_checks',
        'host_acknowledged',
        'host_action_url_expanded',
        'host_active_checks_enabled',
        'host_address',
        'host_check_command',
        'host_check_type',
        'host_comments_with_extra_info',
        'host_custom_variable_names',
        'host_custom_variable_values',
        'host_custom_variables',
        'host_downtimes',
        'host_downtimes_with_extra_info',
        'host_filename',
        'host_has_been_checked',
        'host_icon_image',
        'host_in_check_period',
        'host_in_notification_period',
        'host_in_service_period',
        'host_is_flapping',
        'host_modified_attributes_list',
        'host_name',
        'host_notes_url_expanded',
        'host_notifications_enabled',
        'host_num_services_crit',
        'host_num_services_ok',
        'host_num_services_pending',
        'host_num_services_unknown',
        'host_num_services_warn',
        'host_perf_data',
        'host_pnpgraph_present',
        'host_scheduled_downtime_depth',
        'host_staleness',
        'host_state',
        'some_column',
    ])


def test_get_needed_join_columns(view):
    view_spec = copy.deepcopy(view.spec)
    view_spec["painters"].append(PainterSpec('service_description', None, None, u'CPU load'))
    view = cmk.gui.views.View(view.name, view_spec, view_spec.get("context", {}))

    columns = cmk.gui.views._get_needed_join_columns(view.join_cells, view.sorters)

    expected_columns = [
        'host_name',
        'service_description',
    ]

    if cmk_version.is_managed_edition():
        expected_columns += [
            "host_custom_variables",
        ]

    assert sorted(columns) == sorted(expected_columns)


def test_create_view_basics():
    view_name = "allhosts"
    view_spec = cmk.gui.views.multisite_builtin_views[view_name]
    view = cmk.gui.views.View(view_name, view_spec, view_spec.get("context", {}))

    assert view.name == view_name
    assert view.spec == view_spec
    assert isinstance(view.datasource, cmk.gui.plugins.views.utils.ABCDataSource)
    assert isinstance(view.datasource.table, cmk.gui.plugins.views.utils.RowTable)
    assert view.row_limit is None
    assert view.user_sorters is None
    assert view.want_checkboxes is False
    assert view.only_sites is None


def test_view_row_limit(view):
    assert view.row_limit is None
    view.row_limit = 101
    assert view.row_limit == 101


@pytest.mark.parametrize("limit,permissions,result", [
    (None, [], 1000),

    ("soft", {}, 1000),
    ("hard", {}, 1000),
    ("none", {}, 1000),

    ("soft", {"general.ignore_soft_limit": True}, 1000),
    ("hard", {"general.ignore_soft_limit": True}, 5000),
    # Strange. Shouldn't this stick to the hard limit?
    ("none", {"general.ignore_soft_limit": True}, 1000),

    ("soft", {"general.ignore_soft_limit": True, "general.ignore_hard_limit": True}, 1000),
    ("hard", {"general.ignore_soft_limit": True, "general.ignore_hard_limit": True}, 5000),
    ("none", {"general.ignore_soft_limit": True, "general.ignore_hard_limit": True}, None),
])
def test_gui_view_row_limit(register_builtin_html, monkeypatch, mocker, limit, permissions, result):
    if limit is not None:
        monkeypatch.setitem(html.request._vars, "limit", limit)

    mocker.patch.object(config, "roles", {"nobody": {"permissions": permissions}})
    mocker.patch.object(config.user, "role_ids", ["nobody"])
    assert cmk.gui.views.get_limit() == result


def test_view_only_sites(view):
    assert view.only_sites is None
    view.only_sites = ["unit"]
    assert view.only_sites == ["unit"]


def test_view_user_sorters(view):
    assert view.user_sorters is None
    view.user_sorters = [("abc", True)]
    assert view.user_sorters == [("abc", True)]


def test_view_want_checkboxes(view):
    assert view.want_checkboxes is False
    view.want_checkboxes = True
    assert view.want_checkboxes is True


def test_registered_display_hints():
    expected = ['.',
    '.hardware.',
    '.hardware.chassis.',
    '.hardware.components.',
    '.hardware.components.backplanes:',
    '.hardware.components.backplanes:*.description',
    '.hardware.components.backplanes:*.index',
    '.hardware.components.backplanes:*.location',
    '.hardware.components.backplanes:*.manufacturer',
    '.hardware.components.backplanes:*.model',
    '.hardware.components.backplanes:*.name',
    '.hardware.components.backplanes:*.serial',
    '.hardware.components.backplanes:*.software',
    '.hardware.components.chassis:',
    '.hardware.components.chassis:*.description',
    '.hardware.components.chassis:*.index',
    '.hardware.components.chassis:*.location',
    '.hardware.components.chassis:*.manufacturer',
    '.hardware.components.chassis:*.model',
    '.hardware.components.chassis:*.name',
    '.hardware.components.chassis:*.serial',
    '.hardware.components.chassis:*.software',
    '.hardware.components.containers:',
    '.hardware.components.containers:*.description',
    '.hardware.components.containers:*.index',
    '.hardware.components.containers:*.location',
    '.hardware.components.containers:*.manufacturer',
    '.hardware.components.containers:*.model',
    '.hardware.components.containers:*.name',
    '.hardware.components.containers:*.serial',
    '.hardware.components.containers:*.software',
    '.hardware.components.fans:',
    '.hardware.components.fans:*.description',
    '.hardware.components.fans:*.index',
    '.hardware.components.fans:*.location',
    '.hardware.components.fans:*.manufacturer',
    '.hardware.components.fans:*.model',
    '.hardware.components.fans:*.name',
    '.hardware.components.fans:*.serial',
    '.hardware.components.fans:*.software',
    '.hardware.components.modules:',
    '.hardware.components.modules:*.bootloader',
    '.hardware.components.modules:*.description',
    '.hardware.components.modules:*.firmware',
    '.hardware.components.modules:*.index',
    '.hardware.components.modules:*.location',
    '.hardware.components.modules:*.manufacturer',
    '.hardware.components.modules:*.model',
    '.hardware.components.modules:*.name',
    '.hardware.components.modules:*.serial',
    '.hardware.components.modules:*.software',
    '.hardware.components.modules:*.type',
    '.hardware.components.others:',
    '.hardware.components.others:*.description',
    '.hardware.components.others:*.index',
    '.hardware.components.others:*.location',
    '.hardware.components.others:*.manufacturer',
    '.hardware.components.others:*.model',
    '.hardware.components.others:*.name',
    '.hardware.components.others:*.serial',
    '.hardware.components.others:*.software',
    '.hardware.components.psus:',
    '.hardware.components.psus:*.description',
    '.hardware.components.psus:*.index',
    '.hardware.components.psus:*.location',
    '.hardware.components.psus:*.manufacturer',
    '.hardware.components.psus:*.model',
    '.hardware.components.psus:*.name',
    '.hardware.components.psus:*.serial',
    '.hardware.components.psus:*.software',
    '.hardware.components.sensors:',
    '.hardware.components.sensors:*.description',
    '.hardware.components.sensors:*.index',
    '.hardware.components.sensors:*.location',
    '.hardware.components.sensors:*.manufacturer',
    '.hardware.components.sensors:*.model',
    '.hardware.components.sensors:*.name',
    '.hardware.components.sensors:*.serial',
    '.hardware.components.sensors:*.software',
    '.hardware.components.stacks:',
    '.hardware.components.stacks:*.description',
    '.hardware.components.stacks:*.index',
    '.hardware.components.stacks:*.location',
    '.hardware.components.stacks:*.manufacturer',
    '.hardware.components.stacks:*.model',
    '.hardware.components.stacks:*.name',
    '.hardware.components.stacks:*.serial',
    '.hardware.components.stacks:*.software',
    '.hardware.components.unknowns:',
    '.hardware.components.unknowns:*.description',
    '.hardware.components.unknowns:*.index',
    '.hardware.components.unknowns:*.location',
    '.hardware.components.unknowns:*.manufacturer',
    '.hardware.components.unknowns:*.model',
    '.hardware.components.unknowns:*.name',
    '.hardware.components.unknowns:*.serial',
    '.hardware.components.unknowns:*.software',
    '.hardware.cpu.',
    '.hardware.cpu.arch',
    '.hardware.cpu.bus_speed',
    '.hardware.cpu.cache_size',
    '.hardware.cpu.cores',
    '.hardware.cpu.cores_per_cpu',
    '.hardware.cpu.cpu_max_capa',
    '.hardware.cpu.cpus',
    '.hardware.cpu.entitlement',
    '.hardware.cpu.implementation_mode',
    '.hardware.cpu.logical_cpus',
    '.hardware.cpu.max_speed',
    '.hardware.cpu.model',
    '.hardware.cpu.sharing_mode',
    '.hardware.cpu.smt_threads',
    '.hardware.cpu.threads',
    '.hardware.cpu.threads_per_cpu',
    '.hardware.cpu.voltage',
    '.hardware.memory.',
    '.hardware.memory.arrays:',
    '.hardware.memory.arrays:*.',
    '.hardware.memory.arrays:*.devices:',
    '.hardware.memory.arrays:*.devices:*.',
    '.hardware.memory.arrays:*.devices:*.size',
    '.hardware.memory.arrays:*.devices:*.speed',
    '.hardware.memory.arrays:*.maximum_capacity',
    '.hardware.memory.total_ram_usable',
    '.hardware.memory.total_swap',
    '.hardware.memory.total_vmalloc',
    '.hardware.nwadapter:',
    '.hardware.nwadapter:*.',
    '.hardware.nwadapter:*.gateway',
    '.hardware.nwadapter:*.ipv4_address',
    '.hardware.nwadapter:*.ipv4_subnet',
    '.hardware.nwadapter:*.ipv6_address',
    '.hardware.nwadapter:*.ipv6_subnet',
    '.hardware.nwadapter:*.macaddress',
    '.hardware.nwadapter:*.name',
    '.hardware.nwadapter:*.speed',
    '.hardware.nwadapter:*.type',
    '.hardware.storage.',
    '.hardware.storage.controller.',
    '.hardware.storage.controller.version',
    '.hardware.storage.disks:',
    '.hardware.storage.disks:*.',
    '.hardware.storage.disks:*.bus',
    '.hardware.storage.disks:*.fsnode',
    '.hardware.storage.disks:*.local',
    '.hardware.storage.disks:*.product',
    '.hardware.storage.disks:*.serial',
    '.hardware.storage.disks:*.signature',
    '.hardware.storage.disks:*.size',
    '.hardware.storage.disks:*.type',
    '.hardware.storage.disks:*.vendor',
    '.hardware.system.',
    '.hardware.system.expresscode',
    '.hardware.system.manufacturer',
    '.hardware.system.model',
    '.hardware.system.model_name',
    '.hardware.system.product',
    '.hardware.system.serial',
    '.hardware.system.serial_number',
    '.hardware.video:',
    '.hardware.video:*.',
    '.hardware.video:*.driver',
    '.hardware.video:*.driver_date',
    '.hardware.video:*.driver_version',
    '.hardware.video:*.graphic_memory',
    '.hardware.video:*.name',
    '.hardware.video:*.subsystem',
    '.hardware.volumes.physical_volumes.*:',
    '.hardware.volumes.physical_volumes:*.volume_group_name',
    '.hardware.volumes.physical_volumes:*.physical_volume_name',
    '.hardware.volumes.physical_volumes:*.physical_volume_status',
    '.hardware.volumes.physical_volumes:*.physical_volume_total_partitions',
    '.hardware.volumes.physical_volumes:*.physical_volume_free_partitions',
    '.networking.',
    '.networking.addresses:',
    '.networking.addresses:*.address',
    '.networking.addresses:*.device',
    '.networking.addresses:*.type',
    '.networking.available_ethernet_ports',
    '.networking.interfaces:',
    '.networking.interfaces:*.admin_status',
    '.networking.interfaces:*.alias',
    '.networking.interfaces:*.available',
    '.networking.interfaces:*.description',
    '.networking.interfaces:*.index',
    '.networking.interfaces:*.last_change',
    '.networking.interfaces:*.oper_status',
    '.networking.interfaces:*.phys_address',
    '.networking.interfaces:*.port_type',
    '.networking.interfaces:*.speed',
    '.networking.interfaces:*.vlans',
    '.networking.interfaces:*.vlantype',
    '.networking.routes:',
    '.networking.routes:*.device',
    '.networking.routes:*.gateway',
    '.networking.routes:*.target',
    '.networking.routes:*.type',
    '.networking.total_ethernet_ports',
    '.networking.total_interfaces',
    '.networking.tunnels:',
    '.networking.tunnels:*.index',
    '.networking.tunnels:*.link_priority',
    '.networking.tunnels:*.peerip',
    '.networking.tunnels:*.peername',
    '.networking.tunnels:*.sourceip',
    '.networking.tunnels:*.tunnel_interface',
    '.networking.wlan',
    '.networking.wlan.controller',
    '.networking.wlan.controller.accesspoints:',
    '.networking.wlan.controller.accesspoints:*.group',
    '.networking.wlan.controller.accesspoints:*.ip_addr',
    '.networking.wlan.controller.accesspoints:*.model',
    '.networking.wlan.controller.accesspoints:*.name',
    '.networking.wlan.controller.accesspoints:*.serial',
    '.networking.wlan.controller.accesspoints:*.sys_location',
    '.software.',
    '.software.applications.',
    '.software.applications.check_mk.',
    '.software.applications.check_mk.agent_version',
    '.software.applications.check_mk.cluster.is_cluster',
    '.software.applications.check_mk.cluster.nodes:',
    '.software.applications.check_mk.num_hosts',
    '.software.applications.check_mk.num_services',
    '.software.applications.check_mk.host_labels:',
    '.software.applications.check_mk.host_labels:*.plugin_name',
    '.software.applications.check_mk.host_labels:*.label',
    '.software.applications.check_mk.versions:',
    '.software.applications.check_mk.versions:*.demo',
    '.software.applications.check_mk.sites:',
    '.software.applications.check_mk.sites:*.autostart',
    '.software.applications.check_mk.sites:*.apache',
    '.software.applications.check_mk.sites:*.cmc',
    '.software.applications.check_mk.sites:*.crontab',
    '.software.applications.check_mk.sites:*.dcd',
    '.software.applications.check_mk.sites:*.liveproxyd',
    '.software.applications.check_mk.sites:*.mkeventd',
    '.software.applications.check_mk.sites:*.mknotifyd',
    '.software.applications.check_mk.sites:*.rrdcached',
    '.software.applications.check_mk.sites:*.stunnel',
    '.software.applications.check_mk.sites:*.xinetd',
    '.software.applications.check_mk.sites:*.nagios',
    '.software.applications.check_mk.sites:*.npcd',
    '.software.applications.check_mk.sites:*.check_helper_usage',
    '.software.applications.check_mk.sites:*.check_mk_helper_usage',
    '.software.applications.check_mk.sites:*.fetcher_helper_usage',
    '.software.applications.check_mk.sites:*.checker_helper_usage',
    '.software.applications.check_mk.sites:*.livestatus_usage',
    '.software.applications.check_mk.sites:*.num_hosts',
    '.software.applications.check_mk.sites:*.num_services',
    '.software.applications.check_mk.sites:*.used_version',
    '.software.applications.citrix.',
    '.software.applications.citrix.controller.',
    '.software.applications.citrix.controller.controller_version',
    '.software.applications.citrix.vm.',
    '.software.applications.citrix.vm.agent_version',
    '.software.applications.citrix.vm.catalog',
    '.software.applications.citrix.vm.desktop_group_name',
    '.software.applications.docker.',
    '.software.applications.docker.container.',
    '.software.applications.docker.container.networks:',
    '.software.applications.docker.container.networks:*.ip_address',
    '.software.applications.docker.container.networks:*.ip_prefixlen',
    '.software.applications.docker.container.networks:*.mac_address',
    '.software.applications.docker.container.networks:*.network_id',
    '.software.applications.docker.container.node_name',
    '.software.applications.docker.container.ports:',
    '.software.applications.docker.containers:',
    '.software.applications.docker.containers:*.id',
    '.software.applications.docker.containers:*.labels',
    '.software.applications.docker.images:',
    '.software.applications.docker.images:*.size',
    '.software.applications.docker.images:*.amount_containers',
    '.software.applications.docker.images:*.id',
    '.software.applications.docker.images:*.labels',
    '.software.applications.docker.images:*.repodigests',
    '.software.applications.docker.images:*.repotags',
    '.software.applications.docker.networks.*.',
    '.software.applications.docker.networks.*.containers:',
    '.software.applications.docker.networks.*.containers:*.id',
    '.software.applications.docker.networks.*.containers:*.ipv4_address',
    '.software.applications.docker.networks.*.containers:*.ipv6_address',
    '.software.applications.docker.networks.*.containers:*.mac_address',
    '.software.applications.docker.networks.*.network_id',
    '.software.applications.docker.num_containers_paused',
    '.software.applications.docker.num_containers_running',
    '.software.applications.docker.num_containers_stopped',
    '.software.applications.docker.num_containers_total',
    '.software.applications.docker.num_images',
    '.software.applications.docker.version',
    '.software.applications.ibm_mq.',
    '.software.applications.ibm_mq.channels:',
    '.software.applications.ibm_mq.channels:*.monchl',
    '.software.applications.ibm_mq.channels:*.name',
    '.software.applications.ibm_mq.channels:*.qmgr',
    '.software.applications.ibm_mq.channels:*.status',
    '.software.applications.ibm_mq.channels:*.type',
    '.software.applications.ibm_mq.managers:',
    '.software.applications.ibm_mq.managers:*.ha',
    '.software.applications.ibm_mq.managers:*.instname',
    '.software.applications.ibm_mq.managers:*.instver',
    '.software.applications.ibm_mq.managers:*.name',
    '.software.applications.ibm_mq.managers:*.standby',
    '.software.applications.ibm_mq.managers:*.status',
    '.software.applications.ibm_mq.queues:',
    '.software.applications.ibm_mq.queues:*.altered',
    '.software.applications.ibm_mq.queues:*.created',
    '.software.applications.ibm_mq.queues:*.maxdepth',
    '.software.applications.ibm_mq.queues:*.maxmsgl',
    '.software.applications.ibm_mq.queues:*.monq',
    '.software.applications.ibm_mq.queues:*.name',
    '.software.applications.ibm_mq.queues:*.qmgr',
    '.software.applications.kubernetes.assigned_pods:',
    '.software.applications.kubernetes.assigned_pods:*.name',
    '.software.applications.kubernetes.nodes:',
    '.software.applications.kubernetes.nodes:*.name',
    '.software.applications.kubernetes.ingresses:',
    '.software.applications.kubernetes.pod_container:',
    '.software.applications.kubernetes.pod_container:*.container_id',
    '.software.applications.kubernetes.pod_container:*.image',
    '.software.applications.kubernetes.pod_container:*.image_id',
    '.software.applications.kubernetes.pod_container:*.image_pull_policy',
    '.software.applications.kubernetes.pod_container:*.name',
    '.software.applications.kubernetes.pod_container:*.ready',
    '.software.applications.kubernetes.pod_container:*.restart_count',
    '.software.applications.kubernetes.job_container:',
    '.software.applications.kubernetes.job_container:*.name',
    '.software.applications.kubernetes.job_container:*.image',
    '.software.applications.kubernetes.job_container:*.image_pull_policy',
    '.software.applications.kubernetes.daemon_pod_containers:*.name',
    '.software.applications.kubernetes.daemon_pod_containers:*.image',
    '.software.applications.kubernetes.daemon_pod_containers:*.image_pull_policy',
    '.software.applications.kubernetes.pod_info.',
    '.software.applications.kubernetes.pod_info.dns_policy',
    '.software.applications.kubernetes.pod_info.host_ip',
    '.software.applications.kubernetes.pod_info.host_network',
    '.software.applications.kubernetes.pod_info.node',
    '.software.applications.kubernetes.pod_info.pod_ip',
    '.software.applications.kubernetes.pod_info.qos_class',
    '.software.applications.kubernetes.roles:',
    '.software.applications.kubernetes.roles:*.namespace',
    '.software.applications.kubernetes.roles:*.role',
    '.software.applications.kubernetes.selector.',
    '.software.applications.kubernetes.service_info.',
    '.software.applications.kubernetes.service_info.cluster_ip',
    '.software.applications.kubernetes.service_info.load_balancer_ip',
    '.software.applications.kubernetes.service_info.type',
    '.software.applications.mssql.',
    '.software.applications.mssql.instances:',
    '.software.applications.mssql.instances:*.clustered',
    '.software.applications.oracle.',
    '.software.applications.oracle.dataguard_stats:',
    '.software.applications.oracle.dataguard_stats:*.db_unique',
    '.software.applications.oracle.dataguard_stats:*.role',
    '.software.applications.oracle.dataguard_stats:*.sid',
    '.software.applications.oracle.dataguard_stats:*.switchover',
    '.software.applications.oracle.systemparameter:',
    '.software.applications.oracle.systemparameter:*.sid',
    '.software.applications.oracle.systemparameter:*.name',
    '.software.applications.oracle.systemparameter:*.value',
    '.software.applications.oracle.systemparameter:*.isdefault',
    '.software.applications.oracle.instance:',
    '.software.applications.oracle.instance:*.db_creation_time',
    '.software.applications.oracle.instance:*.db_uptime',
    '.software.applications.oracle.instance:*.logins',
    '.software.applications.oracle.instance:*.logmode',
    '.software.applications.oracle.instance:*.openmode',
    '.software.applications.oracle.instance:*.pname',
    '.software.applications.oracle.instance:*.sid',
    '.software.applications.oracle.instance:*.version',
    '.software.applications.oracle.recovery_area:',
    '.software.applications.oracle.recovery_area:*.flashback',
    '.software.applications.oracle.recovery_area:*.sid',
    ".software.applications.oracle.pga:",
    ".software.applications.oracle.pga:*.aggregate_pga_auto_target",
    ".software.applications.oracle.pga:*.aggregate_pga_target_parameter",
    ".software.applications.oracle.pga:*.bytes_processed",
    ".software.applications.oracle.pga:*.extra_bytes_read_written",
    ".software.applications.oracle.pga:*.global_memory_bound",
    ".software.applications.oracle.pga:*.maximum_pga_allocated",
    ".software.applications.oracle.pga:*.maximum_pga_used_for_auto_workareas",
    ".software.applications.oracle.pga:*.maximum_pga_used_for_manual_workareas",
    ".software.applications.oracle.pga:*.sid",
    ".software.applications.oracle.pga:*.total_freeable_pga_memory",
    ".software.applications.oracle.pga:*.total_pga_allocated",
    ".software.applications.oracle.pga:*.total_pga_inuse",
    ".software.applications.oracle.pga:*.total_pga_used_for_auto_workareas",
    ".software.applications.oracle.pga:*.total_pga_used_for_manual_workareas",
    '.software.applications.oracle.sga:',
    '.software.applications.oracle.sga:*.buf_cache_size',
    '.software.applications.oracle.sga:*.data_trans_cache_size',
    '.software.applications.oracle.sga:*.fixed_size',
    '.software.applications.oracle.sga:*.free_mem_avail',
    '.software.applications.oracle.sga:*.granule_size',
    '.software.applications.oracle.sga:*.in_mem_area_size',
    '.software.applications.oracle.sga:*.java_pool_size',
    '.software.applications.oracle.sga:*.large_pool_size',
    '.software.applications.oracle.sga:*.max_size',
    '.software.applications.oracle.sga:*.redo_buffer',
    '.software.applications.oracle.sga:*.shared_io_pool_size',
    '.software.applications.oracle.sga:*.shared_pool_size',
    '.software.applications.oracle.sga:*.sid',
    '.software.applications.oracle.sga:*.start_oh_shared_pool',
    '.software.applications.oracle.sga:*.streams_pool_size',
    '.software.applications.oracle.tablespaces:',
    '.software.applications.oracle.tablespaces:*.autoextensible',
    '.software.applications.oracle.tablespaces:*.current_size',
    '.software.applications.oracle.tablespaces:*.free_space',
    '.software.applications.oracle.tablespaces:*.increment_size',
    '.software.applications.oracle.tablespaces:*.max_size',
    '.software.applications.oracle.tablespaces:*.name',
    '.software.applications.oracle.tablespaces:*.num_increments',
    '.software.applications.oracle.tablespaces:*.sid',
    '.software.applications.oracle.tablespaces:*.type',
    '.software.applications.oracle.tablespaces:*.used_size',
    '.software.applications.oracle.tablespaces:*.version',
    '.software.applications.vmwareesx:*.',
    '.software.applications.vmwareesx:*.clusters:*.',
    '.software.bios.',
    '.software.bios.date',
    '.software.bios.vendor',
    '.software.bios.version',
    '.software.configuration.',
    '.software.configuration.snmp_info.',
    '.software.configuration.snmp_info.contact',
    '.software.configuration.snmp_info.location',
    '.software.configuration.snmp_info.name',
    '.software.firmware',
    '.software.firmware.platform_level',
    '.software.firmware.vendor',
    '.software.firmware.version',
    '.software.kernel_config:',
    '.software.kernel_config:*.parameter',
    '.software.kernel_config:*.value',
    '.software.os.',
    '.software.os.arch',
    '.software.os.install_date',
    '.software.os.kernel_version',
    '.software.os.name',
    '.software.os.service_pack',
    '.software.os.service_packs:',
    '.software.os.type',
    '.software.os.vendor',
    '.software.os.version',
    '.software.packages:',
    '.software.packages:*.arch',
    '.software.packages:*.install_date',
    '.software.packages:*.name',
    '.software.packages:*.package_type',
    '.software.packages:*.package_version',
    '.software.packages:*.path',
    '.software.packages:*.size',
    '.software.packages:*.summary',
    '.software.packages:*.vendor',
    '.software.packages:*.version',]

    assert sorted(expected) == sorted(cmk.gui.plugins.views.inventory_displayhints.keys())


def test_get_inventory_display_hint():
    hint = cmk.gui.plugins.views.inventory_displayhints.get(".software.packages:*.summary")
    assert isinstance(hint, dict)


def test_view_page(logged_in_wsgi_app, mock_livestatus):
    wsgi_app = logged_in_wsgi_app

    def _prepend(prefix, dict_):
        d = {}
        for key, value in dict_.items():
            d[key] = value
            d[prefix + key] = value
        return d

    custom_variable_names = ['FILENAME', 'ADDRESS_FAMILY', 'ADDRESS_4', 'ADDRESS_6', 'TAGS']
    custom_variable_values = ['/wato/hosts.mk', 4, '127.0.0.1', '', '/wato/ auto-piggyback cmk-agent ip-v4 ip-v4-only lan no-snmp prod site:heute tcp']
    live: MockLiveStatusConnection = mock_livestatus
    live.set_sites(['NO_SITE', 'remote'])
    live.add_table('hosts', [_prepend('host_', {
        'accept_passive_checks': 0,
        'acknowledged': 0,
        'action_url_expanded': '',
        'active_checks_enabled': 1,
        'address': '127.0.0.1',
        'check_command': 'check-mk-host-smart',
        'check_type': 0,
        'comments_with_extra_info': '',
        'custom_variable_name': '',
        'custom_variable_names': custom_variable_names,
        'custom_variable_values': custom_variable_values,
        'custom_variables': dict(zip(custom_variable_names, custom_variable_values)),
        'downtimes': '',
        'downtimes_with_extra_info': '',
        'filename': '/wato/hosts.mk',
        'has_been_checked': 1,
        'icon_image': '',
        'in_check_period': 1,
        'in_notification_period': 1,
        'in_service_period': 1,
        'is_flapping': 0,
        'modified_attributes_list': '',
        'name': 'heute',
        'notes_url_expanded': '',
        'notifications_enabled': 1,
        'num_services_crit': 2,
        'num_services_ok': 37,
        'num_services_pending': 0,
        'num_services_unknown': 0,
        'num_services_warn': 2,
        'perf_data': '',
        'pnpgraph_present': 0,
        'scheduled_downtime_depth': 0,
        'staleness': 0.833333,
        'state': 0,
        'host_labels': {"cmk/os_family": "linux","cmk/check_mk_server": "yes",},
    })])
    live.expect_query("GET hosts\nColumns: filename\nStats: state >= 0")
    live.expect_query(
        "GET hosts\n"
        "Columns: host_accept_passive_checks host_acknowledged host_action_url_expanded "
        "host_active_checks_enabled host_address host_check_command host_check_type "
        "host_comments_with_extra_info host_custom_variable_names host_custom_variable_values host_custom_variables "
        "host_downtimes host_downtimes_with_extra_info host_filename host_has_been_checked "
        "host_icon_image host_in_check_period host_in_notification_period host_in_service_period "
        "host_is_flapping host_labels host_modified_attributes_list host_name host_notes_url_expanded "
        "host_notifications_enabled host_num_services_crit host_num_services_ok "
        "host_num_services_pending host_num_services_unknown host_num_services_warn host_perf_data "
        "host_pnpgraph_present host_scheduled_downtime_depth host_staleness host_state\n"
        "Limit: 1001"
    )
    live.expect_query("GET hosts\nColumns: filename\nStats: state >= 0")
    with live():
        resp = wsgi_app.get("/NO_SITE/check_mk/view.py?view_name=allhosts", status=200)
        assert 'heute' in resp
        assert 'query=null' not in resp
        assert str(resp).count('/domain-types/host/collections/all') == 1
