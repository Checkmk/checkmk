# Make it load all plugins (CEE + CME)
import cmk.gui.views  # pylint: disable=unused-import

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
