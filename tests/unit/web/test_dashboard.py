#!/usr/bin/env python

import cmk.gui.dashboard as dashboard
from cmk.gui.globals import html
import cmk.gui.config as config


def test_dashlet_registry_plugins():
    dashboard._transform_old_dict_based_dashlets()
    assert sorted(dashboard.dashlet_registry.keys()) == sorted([
        'hoststats',
        'notify_failed_notifications',
        'mk_logo',
        'servicestats',
        'url',
        'overview',
        'pnpgraph',
        'view',
        'custom_graph',
        'notify_users',
        'nodata',
        'snapin'
    ])


def _legacy_dashlet_type(attrs=None):
    dashboard.dashlet_types["test123"] = {
        "title": "Test dashlet",
        "description": "Descr",
        "sort_index": 10,
    }
    if attrs:
        dashboard.dashlet_types["test123"].update(attrs)

    dashboard._transform_old_dict_based_dashlets()
    return dashboard.dashlet_registry["test123"]


def test_registry_of_old_dashlet_plugins():
    dashlet_type = _legacy_dashlet_type()
    assert dashlet_type.title() == "Test dashlet"
    assert dashlet_type.description() == "Descr"
    assert dashlet_type.sort_index() == 10


_attr_map = [
    # legacy key, new method name, default value
    ("infos", "infos", []),
    ("single_infos", "single_infos", []),
    ("selectable", "is_selectable", True),
    ("resizable", "is_resizable", True),
    ("size", "size", dashboard.dashlet_min_size),
    ("parameters", "vs_parameters", None),
    ("opt_params", "opt_parameters", None),
    ("validate_params", "validate_parameters_func", None),
    ("refresh", "refresh_interval", False),
    ("allowed", "allowed_roles", config.builtin_role_ids),
    ("styles", "styles", None),
    ("script", "script", None),
    ("title", "title", "Test dashlet"),
]


def test_old_dashlet_defaults():
    dashlet_type = _legacy_dashlet_type()
    dashlet = dashlet_type(dashboard_name="main", dashboard={}, dashlet_id=0, dashlet={}, wato_folder=None)
    for _attr, new_method, deflt in _attr_map:
        assert getattr(dashlet, new_method)() == deflt


def test_old_dashlet_title_func():
    dashlet_type = _legacy_dashlet_type({
        "title_func": lambda d: "xyz",
    })
    dashlet = dashlet_type(dashboard_name="main", dashboard={}, dashlet_id=0, dashlet={}, wato_folder=None)

    assert dashlet.title() == "Test dashlet"
    assert dashlet.display_title() == "xyz"


def test_old_dashlet_on_resize():
    dashlet_type = _legacy_dashlet_type({
        "on_resize": lambda x, y: "xyz",
    })
    dashlet = dashlet_type(dashboard_name="main", dashboard={}, dashlet_id=0, dashlet={}, wato_folder=None)

    assert dashlet.on_resize() == "xyz"


def test_old_dashlet_on_refresh():
    dashlet_type = _legacy_dashlet_type({
        "on_refresh": lambda nr, the_dashlet: "xyz",
    })
    dashlet = dashlet_type(dashboard_name="main", dashboard={}, dashlet_id=0, dashlet={}, wato_folder=None)

    assert dashlet.on_refresh() == "xyz"


def test_old_dashlet_iframe_render(mocker, register_builtin_html):
    iframe_render_mock = mocker.Mock()

    dashlet_type = _legacy_dashlet_type({
        "iframe_render": iframe_render_mock.method,
    })
    dashlet = dashlet_type(dashboard_name="main", dashboard={"mtime": 123}, dashlet_id=1, dashlet={"type": "url"}, wato_folder=None)

    assert dashlet.is_iframe_dashlet()
    dashlet.show()
    assert iframe_render_mock.called_once()

    assert dashlet._get_iframe_url() \
        == "dashboard_dashlet.py?id=1&mtime=123&name=main"


def test_old_dashlet_iframe_urlfunc(mocker, register_builtin_html):
    dashlet_type = _legacy_dashlet_type({
        "iframe_urlfunc": lambda x: "blaurl",
    })
    dashlet = dashlet_type(dashboard_name="main", dashboard={}, dashlet_id=0, dashlet={}, wato_folder=None)

    assert dashlet._get_iframe_url() \
        == "blaurl"


def test_old_dashlet_render(mocker):
    render_mock = mocker.Mock()

    dashlet_type = _legacy_dashlet_type({
        "render": render_mock,
    })
    dashlet = dashlet_type(dashboard_name="main", dashboard={"mtime": 1}, dashlet_id=0, dashlet={"type": "url"}, wato_folder=None)

    assert not dashlet.is_iframe_dashlet()
    dashlet.show()
    assert render_mock.called_once()


def test_old_dashlet_add_urlfunc(mocker):
    dashlet_type = _legacy_dashlet_type({
        "add_urlfunc": lambda: "xyz"
    })
    dashlet = dashlet_type(dashboard_name="main", dashboard={}, dashlet_id=0, dashlet={}, wato_folder=None)
    assert dashlet.add_url() == "xyz"


def test_old_dashlet_settings():
    dashlet_attrs = {}
    for attr, _new_method, _deflt in _attr_map:
        dashlet_attrs[attr] = attr

    dashlet_type = _legacy_dashlet_type(dashlet_attrs)
    dashlet = dashlet_type(dashboard_name="main", dashboard={}, dashlet_id=0, dashlet={}, wato_folder=None)

    for attr, new_method, _deflt in _attr_map:
        assert getattr(dashlet, new_method)() == attr
