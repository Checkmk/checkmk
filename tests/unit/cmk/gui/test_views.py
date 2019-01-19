# Make it load all plugins (CEE + CME)
import cmk.gui.views  # pylint: disable=unused-import
import cmk.gui.default_permissions

from cmk.gui.valuespec import ValueSpec
import cmk.gui.plugins.views


def test_registered_painter_options():
    expected = [
        'aggr_expand',
        'aggr_onlyproblems',
        'aggr_treetype',
        'aggr_wrap',
        'graph_render_options',
        'matrix_omit_uniform',
        'pnp_timerange',
        'show_internal_tree_paths',
        'ts_date',
        'ts_format',
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
        'csv',
        'csv_export',
        'dataset',
        'json',
        'json_export',
        'jsonp',
        'matrix',
        'mobiledataset',
        'mobilelist',
        'mobiletable',
        'python',
        'python-raw',
        'table',
        'tiled',
    ]

    names = cmk.gui.plugins.views.layout_registry.keys()
    assert sorted(expected) == sorted(names)


def test_layout_properties():
    expected = {
        'boxed': {
            'checkboxes': True,
            'hide': False,
            'title': u'Balanced boxes'
        },
        'boxed_graph': {
            'checkboxes': True,
            'hide': False,
            'title': u'Balanced graph boxes'
        },
        'csv': {
            'checkboxes': False,
            'hide': True,
            'title': u'CSV data output'
        },
        'csv_export': {
            'checkboxes': False,
            'hide': True,
            'title': u'CSV data export'
        },
        'dataset': {
            'checkboxes': False,
            'hide': False,
            'title': u'Single dataset'
        },
        'json': {
            'checkboxes': False,
            'hide': True,
            'title': u'JSON data output'
        },
        'json_export': {
            'checkboxes': False,
            'hide': True,
            'title': u'JSON data export'
        },
        'jsonp': {
            'checkboxes': False,
            'hide': True,
            'title': u'JSONP data output'
        },
        'matrix': {
            'checkboxes': False,
            'has_csv_export': True,
            'options': ['matrix_omit_uniform'],
            'hide': False,
            'title': u'Matrix'
        },
        'mobiledataset': {
            'checkboxes': False,
            'hide': False,
            'title': u'Mobile: Dataset'
        },
        'mobilelist': {
            'checkboxes': False,
            'hide': False,
            'title': u'Mobile: List'
        },
        'mobiletable': {
            'checkboxes': False,
            'hide': False,
            'title': u'Mobile: Table'
        },
        'python': {
            'checkboxes': False,
            'hide': True,
            'title': u'Python data output'
        },
        'python-raw': {
            'checkboxes': False,
            'hide': True,
            'title': u'Python raw data output'
        },
        'table': {
            'checkboxes': True,
            'hide': False,
            'title': u'Table'
        },
        'tiled': {
            'checkboxes': True,
            'hide': False,
            'title': u'Tiles'
        },
    }

    for ident, spec in expected.items():
        plugin = cmk.gui.plugins.views.layout_registry[ident]()
        assert isinstance(plugin.title, unicode)
        assert spec["title"] == plugin.title
        assert spec["checkboxes"] == plugin.can_display_checkboxes
        assert spec["hide"] == plugin.is_hidden
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
    expected = {
        'acknowledge': {
            'group': 'acknowledge',
            'permission': 'action.acknowledge',
            'tables': ['host', 'service', 'aggr'],
            'title': u'Acknowledge Problems'
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
            'tables': ['host', 'service'],
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
        'edit_downtimes': {
            'permission': 'action.downtimes',
            'tables': ['downtime'],
            'title': u'Edit Downtimes'
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
    }

    names = cmk.gui.plugins.views.command_registry.keys()
    assert sorted(expected.keys()) == sorted(names)

    for cmd_class in cmk.gui.plugins.views.utils.command_registry.values():
        cmd = cmd_class()
        cmd_spec = expected[cmd.ident]
        assert cmd.title == cmd_spec["title"]
        assert cmd.tables == cmd_spec["tables"], cmd.ident
        assert cmd.permission().name == cmd_spec["permission"]


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


def test_registered_datasources():
    expected = {
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
        if callable(ds.table):
            assert ("func", ds.table.__name__) == spec["table"]
        elif isinstance(ds.table, tuple):
            assert spec["table"][0] == "tuple"
            assert spec["table"][1][0] == ds.table[0].__name__
        else:
            assert ds.table == spec["table"]
        assert ds.keys == spec["keys"]
        assert ds.id_keys == spec["idkeys"]
        assert ds.infos == spec["infos"]
