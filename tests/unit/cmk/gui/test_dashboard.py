#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"
# mypy: disable-error-code="no-untyped-def"
# mypy: disable-error-code="type-arg"


from collections.abc import Iterator
from typing import Literal

import pytest

import cmk.ccc.version as cmk_version
from cmk.ccc.plugin_registry import Registry
from cmk.ccc.user import UserId
from cmk.gui.config import default_authorized_builtin_role_ids
from cmk.gui.dashboard import DashboardConfig, dashlet_registry, DashletConfig
from cmk.gui.dashboard.dashlet.base import Dashlet
from cmk.gui.type_defs import DynamicIconName
from cmk.utils import paths
from tests.testlib.unit.utils import reset_registries


class DummyDashletConfig(DashletConfig): ...


class DummyDashlet(Dashlet[DummyDashletConfig]):
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
    def sort_index(cls) -> int:
        return 123


@pytest.fixture(name="reset_dashlet_registry")
def fixture_reset_dashlet_registry() -> Iterator[None]:
    with reset_registries([dashlet_registry]):
        yield


@pytest.fixture(name="registry_list", scope="module")
def fixture_registry_list() -> list[Registry]:
    """Returns 'dashlet_registry' to be reset after test-case execution."""
    return [dashlet_registry]


@pytest.fixture(name="dummy_config")
def fixture_dummy_config() -> DummyDashletConfig:
    return DummyDashletConfig(
        {
            "type": "dummy",
        }
    )


@pytest.mark.usefixtures("reset_dashlet_registry")
def test_dashlet_registry_plugins() -> None:
    expected_plugins = [
        "hoststats",
        "servicestats",
        "eventstats",
        "notify_failed_notifications",
        "url",
        "pnpgraph",
        "view",
        "embedded_view",
        "linked_view",
        "user_messages",
        "nodata",
        "snapin",
    ]

    if cmk_version.edition(paths.omd_root) is not cmk_version.Edition.COMMUNITY:
        expected_plugins += [
            "alerts_bar_chart",
            "alert_overview",
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
            "top_list",
            "state_host",
            "host_state_summary",
            "service_state_summary",
            "inventory",
        ]

    assert sorted(dashlet_registry.keys()) == sorted(expected_plugins)


def _expected_intervals() -> list[tuple[str, Literal[False] | int]]:
    expected = [
        ("hoststats", False),
        ("nodata", False),
        ("notify_failed_notifications", 60),
        ("user_messages", False),
        ("pnpgraph", 60),
        ("servicestats", False),
        ("snapin", 30),
        ("url", False),
        ("view", False),
        ("linked_view", False),
    ]

    if cmk_version.edition(paths.omd_root) is not cmk_version.Edition.COMMUNITY:
        expected += [
            ("custom_graph", 60),
            ("combined_graph", 60),
            ("problem_graph", 60),
            ("single_timeseries", 60),
        ]

    return expected


TEST_DASHBOARD = DashboardConfig(
    {
        "mandatory_context_filters": [],
        "hidebutton": False,
        "single_infos": [],
        "context": {},
        "mtime": 0,
        "show_title": True,
        "title": "Test",
        "topic": "problems",
        "sort_index": 5,
        "icon": DynamicIconName("dashboard_problems"),
        "description": "",
        "dashlets": [],
        "owner": UserId.builtin(),
        "public": True,
        "name": "problems",
        "hidden": False,
        "link_from": {},
        "add_context_to_title": True,
        "is_show_more": False,
        "packaged": False,
        "main_menu_search_terms": [],
        "embedded_views": {},
    }
)


@pytest.mark.usefixtures("request_context")
def test_dashlet_type_defaults() -> None:
    assert not Dashlet.single_infos()
    assert Dashlet.is_selectable() is True
    assert Dashlet.is_resizable() is True
    assert Dashlet.initial_size() == Dashlet.minimum_size
    assert Dashlet.initial_position() == (1, 1)
    assert Dashlet.allowed_roles() == default_authorized_builtin_role_ids


def test_dashlet_defaults(dummy_config: DummyDashletConfig) -> None:
    dashlet = DummyDashlet(
        dashboard_name="main",
        dashboard_owner=UserId.builtin(),
        dashboard=TEST_DASHBOARD,
        dashlet_id=1,
        dashlet=dummy_config,
    )
    assert not dashlet.infos()
    assert dashlet.dashlet_id == 1
    assert dashlet.dashlet_spec == {"type": "dummy"}
    assert dashlet.dashboard_name == "main"


def test_dashlet_title(dummy_config: DummyDashletConfig) -> None:
    dashlet = DummyDashlet(
        dashboard_name="main",
        dashboard_owner=UserId.builtin(),
        dashboard=TEST_DASHBOARD,
        dashlet_id=1,
        dashlet=dummy_config,
    )
    assert dashlet.display_title() == "DUMMy"

    dummy_config["title"] = "abc"
    dashlet = DummyDashlet(
        dashboard_name="main",
        dashboard_owner=UserId.builtin(),
        dashboard=TEST_DASHBOARD,
        dashlet_id=1,
        dashlet=dummy_config,
    )
    assert dashlet.display_title() == "abc"


def test_show_title(dummy_config: DummyDashletConfig) -> None:
    dashlet = DummyDashlet(
        dashboard_name="main",
        dashboard_owner=UserId.builtin(),
        dashboard=TEST_DASHBOARD,
        dashlet_id=1,
        dashlet=dummy_config,
    )
    assert dashlet.show_title() is True

    dummy_config["show_title"] = False
    dashlet = DummyDashlet(
        dashboard_name="main",
        dashboard_owner=UserId.builtin(),
        dashboard=TEST_DASHBOARD,
        dashlet_id=1,
        dashlet=dummy_config,
    )
    assert dashlet.show_title() is False


def test_title_url(dummy_config: DummyDashletConfig) -> None:
    dashlet = DummyDashlet(
        dashboard_name="main",
        dashboard_owner=UserId.builtin(),
        dashboard=TEST_DASHBOARD,
        dashlet_id=1,
        dashlet=dummy_config,
    )
    assert dashlet.title_url() is None

    dummy_config["title_url"] = "index.py?bla=blub"
    dashlet = DummyDashlet(
        dashboard_name="main",
        dashboard_owner=UserId.builtin(),
        dashboard=TEST_DASHBOARD,
        dashlet_id=1,
        dashlet=dummy_config,
    )
    assert dashlet.title_url() == "index.py?bla=blub"


def test_show_background(dummy_config: DummyDashletConfig) -> None:
    dashlet = DummyDashlet(
        dashboard_name="main",
        dashboard_owner=UserId.builtin(),
        dashboard=TEST_DASHBOARD,
        dashlet_id=1,
        dashlet=dummy_config,
    )
    assert dashlet.show_background() is True

    dummy_config["background"] = False
    dashlet = DummyDashlet(
        dashboard_name="main",
        dashboard_owner=UserId.builtin(),
        dashboard=TEST_DASHBOARD,
        dashlet_id=1,
        dashlet=dummy_config,
    )
    assert dashlet.show_background() is False


@pytest.mark.usefixtures("reset_dashlet_registry")
def test_dashlet_context_inheritance() -> None:
    test_dashboard = TEST_DASHBOARD.copy()
    test_dashboard["context"] = {
        "wato_folder": {"wato_folder": "/aaa/eee"},
        "host": {"host": "bla", "neg_host": ""},
    }

    dashboard_spec = test_dashboard

    dashlet_spec = {
        "type": "hoststats",
        "context": {"wato_folder": {"wato_folder": ""}},
        "single_infos": [],
        "show_title": True,
        "title": "Host Statistics",
        "add_context_to_title": True,
        "link_from": {},
        "position": (61, 1),
        "size": (30, 18),
    }

    HostStats = dashlet_registry["hoststats"]
    dashlet = HostStats(
        dashboard_name="bla",
        dashboard_owner=UserId.builtin(),
        dashboard=dashboard_spec,
        dashlet_id=1,
        dashlet=dashlet_spec,
    )

    assert dashlet.context == {
        "host": {"host": "bla", "neg_host": ""},
        "wato_folder": {"wato_folder": ""},
    }

    assert sorted(dashlet._dashlet_context_vars()) == sorted(
        [("host", "bla"), ("neg_host", ""), ("wato_folder", "")]
    )
