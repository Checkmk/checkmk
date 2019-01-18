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
