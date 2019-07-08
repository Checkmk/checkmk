#!/usr/bin/env python

import cmk.gui.dashboard as dashboard
from cmk.gui.globals import html
import cmk.gui.config as config


class DummyDashlet(dashboard.Dashlet):
    @classmethod
    def type_name(cls):
        return "dummy"

    @classmethod
    def title(cls):
        return "DUMMy"

    @classmethod
    def description(cls):
        return "duMMy"

    @classmethod
    def sort_index(cls):
        return 123

    def show(self):
        html.write("dummy")


def test_dashlet_registry_plugins():
    dashboard._transform_old_dict_based_dashlets()
    assert sorted(dashboard.dashlet_registry.keys()) == sorted([
        'hoststats', 'notify_failed_notifications', 'mk_logo', 'network_topology', 'servicestats',
        'url', 'overview', 'pnpgraph', 'view', 'custom_graph', 'notify_users', 'nodata', 'snapin'
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
    ("size", "initial_size", dashboard.Dashlet.minimum_size),
    ("parameters", "vs_parameters", None),
    ("opt_params", "opt_parameters", None),
    ("validate_params", "validate_parameters_func", None),
    ("refresh", "initial_refresh_interval", False),
    ("allowed", "allowed_roles", config.builtin_role_ids),
    ("styles", "styles", None),
    ("script", "script", None),
    ("title", "title", "Test dashlet"),
]


def test_old_dashlet_defaults():
    dashlet_type = _legacy_dashlet_type()
    dashlet = dashlet_type(dashboard_name="main",
                           dashboard={},
                           dashlet_id=0,
                           dashlet={},
                           wato_folder=None)
    for _attr, new_method, deflt in _attr_map:
        assert getattr(dashlet, new_method)() == deflt


def test_old_dashlet_title_func():
    dashlet_type = _legacy_dashlet_type({
        "title_func": lambda d: "xyz",
    })
    dashlet = dashlet_type(dashboard_name="main",
                           dashboard={},
                           dashlet_id=0,
                           dashlet={},
                           wato_folder=None)

    assert dashlet.title() == "Test dashlet"
    assert dashlet.display_title() == "xyz"


def test_old_dashlet_on_resize():
    dashlet_type = _legacy_dashlet_type({
        "on_resize": lambda x, y: "xyz",
    })
    dashlet = dashlet_type(dashboard_name="main",
                           dashboard={},
                           dashlet_id=0,
                           dashlet={},
                           wato_folder=None)

    assert dashlet.on_resize() == "xyz"


def test_old_dashlet_on_refresh():
    dashlet_type = _legacy_dashlet_type({
        "on_refresh": lambda nr, the_dashlet: "xyz",
    })
    dashlet = dashlet_type(dashboard_name="main",
                           dashboard={},
                           dashlet_id=0,
                           dashlet={},
                           wato_folder=None)

    assert dashlet.on_refresh() == "xyz"


def test_old_dashlet_iframe_render(mocker, register_builtin_html):
    iframe_render_mock = mocker.Mock()

    dashlet_type = _legacy_dashlet_type({
        "iframe_render": iframe_render_mock.method,
    })
    dashlet = dashlet_type(dashboard_name="main",
                           dashboard={"mtime": 123},
                           dashlet_id=1,
                           dashlet={"type": "url"},
                           wato_folder=None)

    assert dashlet.is_iframe_dashlet()
    dashlet.show()
    assert iframe_render_mock.called_once()

    assert dashlet._get_iframe_url() \
        == "dashboard_dashlet.py?id=1&mtime=123&name=main"


def test_old_dashlet_iframe_urlfunc(mocker, register_builtin_html):
    dashlet_type = _legacy_dashlet_type({
        "iframe_urlfunc": lambda x: "blaurl",
    })
    dashlet = dashlet_type(dashboard_name="main",
                           dashboard={},
                           dashlet_id=0,
                           dashlet={},
                           wato_folder=None)

    assert dashlet._get_iframe_url() \
        == "blaurl"


def test_old_dashlet_render(mocker, register_builtin_html):
    render_mock = mocker.Mock()

    dashlet_type = _legacy_dashlet_type({
        "render": render_mock,
    })
    dashlet = dashlet_type(dashboard_name="main",
                           dashboard={"mtime": 1},
                           dashlet_id=0,
                           dashlet={"type": "url"},
                           wato_folder=None)

    assert not dashlet.is_iframe_dashlet()
    dashlet.show()
    assert render_mock.called_once()


def test_old_dashlet_add_urlfunc(mocker):
    dashlet_type = _legacy_dashlet_type({"add_urlfunc": lambda: "xyz"})
    dashlet = dashlet_type(dashboard_name="main",
                           dashboard={},
                           dashlet_id=0,
                           dashlet={},
                           wato_folder=None)
    assert dashlet.add_url() == "xyz"


def test_old_dashlet_position(mocker):
    dashlet_type = _legacy_dashlet_type({})
    assert dashlet_type.initial_position() == (1, 1)

    dashlet = dashlet_type(dashboard_name="main",
                           dashboard={},
                           dashlet_id=0,
                           dashlet={},
                           wato_folder=None)
    assert dashlet.position() == (1, 1)

    dashlet = dashlet_type(dashboard_name="main",
                           dashboard={},
                           dashlet_id=0,
                           dashlet={"position": (10, 12)},
                           wato_folder=None)
    assert dashlet.position() == (10, 12)


def test_old_dashlet_size(mocker):
    dashlet_type = _legacy_dashlet_type({})
    assert dashlet_type.initial_size() == (10, 5)

    dashlet_type = _legacy_dashlet_type({"size": (25, 10)})
    assert dashlet_type.initial_size() == (25, 10)

    dashlet = dashlet_type(dashboard_name="main",
                           dashboard={},
                           dashlet_id=0,
                           dashlet={},
                           wato_folder=None)
    assert dashlet.size() == (25, 10)

    dashlet = dashlet_type(dashboard_name="main",
                           dashboard={},
                           dashlet_id=0,
                           dashlet={"size": (30, 20)},
                           wato_folder=None)
    assert dashlet.size() == (30, 20)


def test_old_dashlet_settings():
    dashlet_attrs = {}
    for attr, _new_method, _deflt in _attr_map:
        dashlet_attrs[attr] = attr

    dashlet_type = _legacy_dashlet_type(dashlet_attrs)
    dashlet = dashlet_type(dashboard_name="main",
                           dashboard={},
                           dashlet_id=0,
                           dashlet={},
                           wato_folder=None)

    for attr, new_method, _deflt in _attr_map:
        assert getattr(dashlet, new_method)() == attr


def test_dashlet_type_defaults(register_builtin_html):
    assert dashboard.Dashlet.infos() == []
    assert dashboard.Dashlet.single_infos() == []
    assert dashboard.Dashlet.is_selectable() == True
    assert dashboard.Dashlet.is_resizable() == True
    assert dashboard.Dashlet.is_iframe_dashlet() == False
    assert dashboard.Dashlet.initial_size() == dashboard.Dashlet.minimum_size
    assert dashboard.Dashlet.initial_position() == (1, 1)
    assert dashboard.Dashlet.initial_refresh_interval() == False
    assert dashboard.Dashlet.vs_parameters() is None
    assert dashboard.Dashlet.opt_parameters() is None
    assert dashboard.Dashlet.validate_parameters_func() is None
    assert dashboard.Dashlet.styles() is None
    assert dashboard.Dashlet.script() is None
    assert dashboard.Dashlet.allowed_roles() == config.builtin_role_ids

    assert DummyDashlet.add_url() == "edit_dashlet.py?back=index.py%3Fedit%3D1&type=dummy"


def test_dashlet_defaults():
    dashlet = DummyDashlet(dashboard_name="main",
                           dashboard={},
                           dashlet_id=1,
                           dashlet={"xyz": "abc"},
                           wato_folder="xyz")
    assert dashlet.dashlet_id == 1
    assert dashlet.dashlet_spec == {"xyz": "abc"}
    assert dashlet.wato_folder == "xyz"
    assert dashlet.dashboard_name == "main"


def test_dashlet_title():
    dashlet = DummyDashlet(dashboard_name="main",
                           dashboard={},
                           dashlet_id=1,
                           dashlet={"title": "abc"},
                           wato_folder="xyz")
    assert dashlet.display_title() == "abc"

    dashlet = DummyDashlet(dashboard_name="main",
                           dashboard={},
                           dashlet_id=1,
                           dashlet={},
                           wato_folder="xyz")
    assert dashlet.display_title() == "DUMMy"


def test_show_title():
    dashlet = DummyDashlet(dashboard_name="main",
                           dashboard={},
                           dashlet_id=1,
                           dashlet={},
                           wato_folder="xyz")
    assert dashlet.show_title() == True

    dashlet = DummyDashlet(dashboard_name="main",
                           dashboard={},
                           dashlet_id=1,
                           dashlet={"show_title": False},
                           wato_folder="xyz")
    assert dashlet.show_title() == False


def test_title_url():
    dashlet = DummyDashlet(dashboard_name="main",
                           dashboard={},
                           dashlet_id=1,
                           dashlet={},
                           wato_folder="xyz")
    assert dashlet.title_url() is None

    dashlet = DummyDashlet(dashboard_name="main",
                           dashboard={},
                           dashlet_id=1,
                           dashlet={"title_url": "index.py?bla=blub"},
                           wato_folder="xyz")
    assert dashlet.title_url() == "index.py?bla=blub"


def test_show_background():
    dashlet = DummyDashlet(dashboard_name="main",
                           dashboard={},
                           dashlet_id=1,
                           dashlet={},
                           wato_folder="xyz")
    assert dashlet.show_background() == True

    dashlet = DummyDashlet(dashboard_name="main",
                           dashboard={},
                           dashlet_id=1,
                           dashlet={"background": False},
                           wato_folder="xyz")
    assert dashlet.show_background() == False


def test_on_resize():
    dashlet = DummyDashlet(dashboard_name="main",
                           dashboard={},
                           dashlet_id=1,
                           dashlet={},
                           wato_folder="xyz")
    assert dashlet.on_resize() is None


def test_on_refresh():
    dashlet = DummyDashlet(dashboard_name="main",
                           dashboard={},
                           dashlet_id=1,
                           dashlet={},
                           wato_folder="xyz")
    assert dashlet.on_refresh() is None


def test_size():
    dashlet = DummyDashlet(dashboard_name="main",
                           dashboard={},
                           dashlet_id=1,
                           dashlet={},
                           wato_folder="xyz")
    assert dashlet.size() == DummyDashlet.initial_size()

    dashlet = DummyDashlet(dashboard_name="main",
                           dashboard={},
                           dashlet_id=1,
                           dashlet={"size": (22, 33)},
                           wato_folder="xyz")
    assert dashlet.size() == (22, 33)

    class NotResizable(DummyDashlet):
        @classmethod
        def is_resizable(cls):
            return False

    dashlet = NotResizable(dashboard_name="main",
                           dashboard={},
                           dashlet_id=1,
                           dashlet={"size": (22, 33)},
                           wato_folder="xyz")
    assert dashlet.size() == NotResizable.initial_size()


def test_position():
    dashlet = DummyDashlet(dashboard_name="main",
                           dashboard={},
                           dashlet_id=1,
                           dashlet={},
                           wato_folder="xyz")
    assert dashlet.position() == DummyDashlet.initial_position()

    dashlet = DummyDashlet(dashboard_name="main",
                           dashboard={},
                           dashlet_id=1,
                           dashlet={"position": (4, 4)},
                           wato_folder="xyz")
    assert dashlet.position() == (4, 4)


def test_refresh_interval():
    dashlet = DummyDashlet(dashboard_name="main",
                           dashboard={},
                           dashlet_id=1,
                           dashlet={},
                           wato_folder="xyz")
    assert dashlet.refresh_interval() == DummyDashlet.initial_refresh_interval()

    dashlet = DummyDashlet(dashboard_name="main",
                           dashboard={},
                           dashlet_id=1,
                           dashlet={"refresh": 22},
                           wato_folder="xyz")
    assert dashlet.refresh_interval() == 22
