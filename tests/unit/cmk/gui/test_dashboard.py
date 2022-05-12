#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

import cmk.utils.version as cmk_version

import cmk.gui.dashboard as dashboard  # pylint: disable=reimported
from cmk.gui.config import builtin_role_ids
from cmk.gui.htmllib.html import html


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
        html.write_text("dummy")


def test_dashlet_registry_plugins():
    expected_plugins = [
        "hoststats",
        "servicestats",
        "eventstats",
        "notify_failed_notifications",
        "mk_logo",
        "url",
        "overview",
        "pnpgraph",
        "view",
        "linked_view",
        "user_messages",
        "nodata",
        "snapin",
    ]

    if not cmk_version.is_raw_edition():
        expected_plugins += [
            "alerts_bar_chart",
            "alert_statistics",
            "average_scatterplot",
            "barplot",
            "gauge",
            "notifications_bar_chart",
            "problem_graph",
            "single_metric",
            "site_overview",
            "custom_graph",
            "combined_graph",
            "ntop_alerts",
            "ntop_flows",
            "ntop_top_talkers",
            "single_timeseries",
            "state_service",
            "state_host",
            "host_state_summary",
            "service_state_summary",
            "inventory",
        ]

    dashboard._transform_old_dict_based_dashlets()
    assert sorted(dashboard.dashlet_registry.keys()) == sorted(expected_plugins)


def _expected_intervals():
    expected = [
        ("hoststats", False),
        ("mk_logo", False),
        ("nodata", False),
        ("notify_failed_notifications", 60),
        ("user_messages", False),
        ("overview", False),
        ("pnpgraph", 60),
        ("servicestats", False),
        ("snapin", 30),
        ("url", False),
        ("view", False),
        ("linked_view", False),
    ]

    if not cmk_version.is_raw_edition():
        expected += [
            ("custom_graph", 60),
        ]

    return expected


@pytest.mark.parametrize("type_name,expected_refresh_interval", _expected_intervals())
def test_dashlet_refresh_intervals(
    request_context, type_name, expected_refresh_interval, monkeypatch
):
    dashlet_type = dashboard.dashlet_registry[type_name]
    assert dashlet_type.initial_refresh_interval() == expected_refresh_interval

    dashlet_spec = {
        "type": type_name,
    }
    if dashlet_type.has_context():
        dashlet_spec["context"] = {}
    if type_name in ["pnpgraph", "custom_graph"]:
        monkeypatch.setattr(dashlet_type, "graph_identification", lambda s, c: ("template", {}))
        monkeypatch.setattr(
            "cmk.gui.plugins.metrics.html_render.resolve_graph_recipe",
            lambda g, d: [{"title": "1"}],
        )

    monkeypatch.setattr(dashboard.Dashlet, "_get_context", lambda s: {})

    dashlet = dashlet_type(
        dashboard_name="main",
        dashboard=dashboard._add_context_to_dashboard({}),
        dashlet_id=1,
        dashlet=dashlet_spec,
    )

    assert dashlet.refresh_interval() == expected_refresh_interval


@pytest.fixture(name="reset_dashlet_types")
def _reset_dashlet_types():
    default_entries = list(dashboard.dashlet_types)
    try:
        yield
    finally:
        for entry in list(dashboard.dashlet_types):
            if entry not in default_entries:
                del dashboard.dashlet_types[entry]


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


def test_registry_of_old_dashlet_plugins(reset_dashlet_types):
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
    ("opt_params", "opt_parameters", False),
    ("validate_params", "validate_parameters_func", None),
    ("refresh", "initial_refresh_interval", False),
    ("allowed", "allowed_roles", builtin_role_ids),
    ("styles", "styles", None),
    ("script", "script", None),
    ("title", "title", "Test dashlet"),
]


def test_old_dashlet_defaults(reset_dashlet_types):
    dashlet_type = _legacy_dashlet_type()
    dashlet = dashlet_type(dashboard_name="main", dashboard={}, dashlet_id=0, dashlet={})
    for _attr, new_method, deflt in _attr_map:
        assert getattr(dashlet, new_method)() == deflt


def test_old_dashlet_title_func(reset_dashlet_types):
    dashlet_type = _legacy_dashlet_type(
        {
            "title_func": lambda d: "xyz",
        }
    )
    dashlet = dashlet_type(dashboard_name="main", dashboard={}, dashlet_id=0, dashlet={})

    assert dashlet.title() == "Test dashlet"
    assert dashlet.display_title() == "xyz"


def test_old_dashlet_on_resize(reset_dashlet_types):
    dashlet_type = _legacy_dashlet_type(
        {
            "on_resize": lambda x, y: "xyz",
        }
    )
    dashlet = dashlet_type(dashboard_name="main", dashboard={}, dashlet_id=0, dashlet={})

    assert dashlet.on_resize() == "xyz"


def test_old_dashlet_on_refresh(reset_dashlet_types):
    dashlet_type = _legacy_dashlet_type(
        {
            "on_refresh": lambda nr, the_dashlet: "xyz",
        }
    )
    dashlet = dashlet_type(dashboard_name="main", dashboard={}, dashlet_id=0, dashlet={})

    assert dashlet.on_refresh() == "xyz"


def test_old_dashlet_iframe_render(mocker, request_context, reset_dashlet_types):
    iframe_render_mock = mocker.Mock()

    dashlet_type = _legacy_dashlet_type(
        {
            "iframe_render": iframe_render_mock.method,
        }
    )
    dashlet = dashlet_type(
        dashboard_name="main",
        dashboard=dashboard._add_context_to_dashboard({"mtime": 123}),
        dashlet_id=1,
        dashlet={"type": "url"},
    )

    assert dashlet.is_iframe_dashlet()
    dashlet.show()
    assert iframe_render_mock.called_once()

    assert dashlet._get_iframe_url() == "dashboard_dashlet.py?id=1&mtime=123&name=main"


def test_old_dashlet_iframe_urlfunc(mocker, request_context, reset_dashlet_types):
    dashlet_type = _legacy_dashlet_type(
        {
            "iframe_urlfunc": lambda x: "blaurl",
        }
    )
    dashlet = dashlet_type(dashboard_name="main", dashboard={}, dashlet_id=0, dashlet={})

    assert dashlet._get_iframe_url() == "blaurl"


def test_old_dashlet_render(mocker, request_context, reset_dashlet_types):
    render_mock = mocker.Mock()

    dashlet_type = _legacy_dashlet_type(
        {
            "render": render_mock,
        }
    )
    dashlet = dashlet_type(
        dashboard_name="main", dashboard={"mtime": 1}, dashlet_id=0, dashlet={"type": "url"}
    )

    assert not dashlet.is_iframe_dashlet()
    dashlet.show()
    assert render_mock.called_once()


def test_old_dashlet_add_urlfunc(mocker, reset_dashlet_types):
    dashlet_type = _legacy_dashlet_type({"add_urlfunc": lambda: "xyz"})
    dashlet = dashlet_type(dashboard_name="main", dashboard={}, dashlet_id=0, dashlet={})
    assert dashlet.add_url() == "xyz"


def test_old_dashlet_position(mocker, reset_dashlet_types):
    dashlet_type = _legacy_dashlet_type({})
    assert dashlet_type.initial_position() == (1, 1)

    dashlet = dashlet_type(dashboard_name="main", dashboard={}, dashlet_id=0, dashlet={})
    assert dashlet.position() == (1, 1)

    dashlet = dashlet_type(
        dashboard_name="main", dashboard={}, dashlet_id=0, dashlet={"position": (10, 12)}
    )
    assert dashlet.position() == (10, 12)


def test_old_dashlet_size(mocker, reset_dashlet_types):
    dashlet_type = _legacy_dashlet_type({})
    assert dashlet_type.initial_size() == (12, 12)

    dashlet_type = _legacy_dashlet_type({"size": (25, 10)})
    assert dashlet_type.initial_size() == (25, 10)

    dashlet = dashlet_type(dashboard_name="main", dashboard={}, dashlet_id=0, dashlet={})
    assert dashlet.size() == (25, 10)

    dashlet = dashlet_type(
        dashboard_name="main", dashboard={}, dashlet_id=0, dashlet={"size": (30, 20)}
    )
    assert dashlet.size() == (30, 20)


def test_old_dashlet_settings(reset_dashlet_types):
    dashlet_attrs = {}
    for attr, _new_method, _deflt in _attr_map:
        dashlet_attrs[attr] = attr

    dashlet_type = _legacy_dashlet_type(dashlet_attrs)
    dashlet = dashlet_type(dashboard_name="main", dashboard={}, dashlet_id=0, dashlet={})

    for attr, new_method, _deflt in _attr_map:
        assert getattr(dashlet, new_method)() == attr


def test_dashlet_type_defaults(request_context):
    assert dashboard.Dashlet.single_infos() == []
    assert dashboard.Dashlet.is_selectable() is True
    assert dashboard.Dashlet.is_resizable() is True
    assert dashboard.Dashlet.is_iframe_dashlet() is False
    assert dashboard.Dashlet.initial_size() == dashboard.Dashlet.minimum_size
    assert dashboard.Dashlet.initial_position() == (1, 1)
    assert dashboard.Dashlet.initial_refresh_interval() is False
    assert dashboard.Dashlet.vs_parameters() is None
    assert dashboard.Dashlet.opt_parameters() is False
    assert dashboard.Dashlet.validate_parameters_func() is None
    assert dashboard.Dashlet.styles() is None
    assert dashboard.Dashlet.script() is None
    assert dashboard.Dashlet.allowed_roles() == builtin_role_ids

    assert DummyDashlet.add_url() == "edit_dashlet.py?back=index.py%3Fedit%3D1&type=dummy"


def test_dashlet_defaults():
    dashlet = DummyDashlet(
        dashboard_name="main", dashboard={}, dashlet_id=1, dashlet={"xyz": "abc"}
    )
    assert dashlet.infos() == []
    assert dashlet.dashlet_id == 1
    assert dashlet.dashlet_spec == {"xyz": "abc"}
    assert dashlet.dashboard_name == "main"


def test_dashlet_title():
    dashlet = DummyDashlet(
        dashboard_name="main", dashboard={}, dashlet_id=1, dashlet={"title": "abc"}
    )
    assert dashlet.display_title() == "abc"

    dashlet = DummyDashlet(dashboard_name="main", dashboard={}, dashlet_id=1, dashlet={})
    assert dashlet.display_title() == "DUMMy"


def test_show_title():
    dashlet = DummyDashlet(dashboard_name="main", dashboard={}, dashlet_id=1, dashlet={})
    assert dashlet.show_title() is True

    dashlet = DummyDashlet(
        dashboard_name="main", dashboard={}, dashlet_id=1, dashlet={"show_title": False}
    )
    assert dashlet.show_title() is False


def test_title_url():
    dashlet = DummyDashlet(dashboard_name="main", dashboard={}, dashlet_id=1, dashlet={})
    assert dashlet.title_url() is None

    dashlet = DummyDashlet(
        dashboard_name="main",
        dashboard={},
        dashlet_id=1,
        dashlet={"title_url": "index.py?bla=blub"},
    )
    assert dashlet.title_url() == "index.py?bla=blub"


def test_show_background():
    dashlet = DummyDashlet(dashboard_name="main", dashboard={}, dashlet_id=1, dashlet={})
    assert dashlet.show_background() is True

    dashlet = DummyDashlet(
        dashboard_name="main", dashboard={}, dashlet_id=1, dashlet={"background": False}
    )
    assert dashlet.show_background() is False


def test_on_resize():
    dashlet = DummyDashlet(dashboard_name="main", dashboard={}, dashlet_id=1, dashlet={})
    assert dashlet.on_resize() is None


def test_on_refresh():
    dashlet = DummyDashlet(dashboard_name="main", dashboard={}, dashlet_id=1, dashlet={})
    assert dashlet.on_refresh() is None


def test_size():
    dashlet = DummyDashlet(dashboard_name="main", dashboard={}, dashlet_id=1, dashlet={})
    assert dashlet.size() == DummyDashlet.initial_size()

    dashlet = DummyDashlet(
        dashboard_name="main", dashboard={}, dashlet_id=1, dashlet={"size": (22, 33)}
    )
    assert dashlet.size() == (22, 33)

    class NotResizable(DummyDashlet):
        @classmethod
        def is_resizable(cls):
            return False

    dashlet = NotResizable(
        dashboard_name="main", dashboard={}, dashlet_id=1, dashlet={"size": (22, 33)}
    )
    assert dashlet.size() == NotResizable.initial_size()


def test_position():
    dashlet = DummyDashlet(dashboard_name="main", dashboard={}, dashlet_id=1, dashlet={})
    assert dashlet.position() == DummyDashlet.initial_position()

    dashlet = DummyDashlet(
        dashboard_name="main", dashboard={}, dashlet_id=1, dashlet={"position": (4, 4)}
    )
    assert dashlet.position() == (4, 4)


def test_refresh_interval():
    dashlet = DummyDashlet(dashboard_name="main", dashboard={}, dashlet_id=1, dashlet={})
    assert dashlet.refresh_interval() == DummyDashlet.initial_refresh_interval()

    dashlet = DummyDashlet(
        dashboard_name="main", dashboard={}, dashlet_id=1, dashlet={"refresh": 22}
    )
    assert dashlet.refresh_interval() == 22


def test_dashlet_context_inheritance():
    dashboard_spec = dashboard._add_context_to_dashboard(
        {
            "context": {
                "wato_folder": {"wato_folder": "/aaa/eee"},
                "host": {"host": "bla", "neg_host": ""},
            }
        }
    )

    dashlet_spec = {
        "type": "hoststats",
        "context": {"wato_folder": {"wato_folder": ""}},
        "single_infos": [],
        "show_title": True,
        "title": "Host Statistics",
        "refresh": 60,
        "add_context_to_title": True,
        "link_from": {},
        "position": (61, 1),
        "size": (30, 18),
    }

    HostStats = dashboard.dashlet_registry["hoststats"]
    dashlet = HostStats(
        dashboard_name="bla", dashboard=dashboard_spec, dashlet_id=1, dashlet=dashlet_spec
    )

    assert dashlet.context == {
        "host": {"host": "bla", "neg_host": ""},
        "wato_folder": {"wato_folder": ""},
    }

    assert sorted(dashlet._dashlet_context_vars()) == sorted(
        [("host", "bla"), ("neg_host", ""), ("wato_folder", "")]
    )
