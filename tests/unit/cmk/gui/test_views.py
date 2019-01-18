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
