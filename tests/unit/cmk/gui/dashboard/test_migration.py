#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator
from unittest.mock import MagicMock, patch

import pytest

from cmk.ccc.user import UserId
from cmk.gui.dashboard.dashlet import StatsDashletConfig
from cmk.gui.dashboard.store import (
    _internal_dashboard_to_runtime_dashboard,
    MaybeOldDashboardConfig,
    migrate_dashboard_config,
)
from cmk.gui.dashboard.type_defs import ViewDashletConfig
from cmk.gui.type_defs import DashboardEmbeddedViewSpec


def _make_dashboard(**overrides: object) -> MaybeOldDashboardConfig:
    """Create a minimal dashboard dict with all required Visual + DashboardConfig fields."""
    base: MaybeOldDashboardConfig = {
        "owner": UserId("test_user"),
        "name": "test_dashboard",
        "context": {},
        "single_infos": [],
        "add_context_to_title": True,
        "title": "Test",
        "description": "",
        "topic": "overview",
        "sort_index": 0,
        "is_show_more": False,
        "icon": None,
        "hidden": False,
        "hidebutton": False,
        "public": False,
        "packaged": False,
        "link_from": {},
        "main_menu_search_terms": [],
        "mtime": 0,
        "widgets": {},
        "show_title": True,
        "mandatory_context_filters": [],
        "embedded_views": {},
    }
    base.update(overrides)  # type: ignore[typeddict-item]
    return base


def _make_view_widget(**overrides: object) -> ViewDashletConfig:
    """Create a minimal ViewDashletConfig"""
    base: ViewDashletConfig = {
        "type": "view",
        "name": "test_view",
        "single_infos": ["host"],
        "datasource": "hosts",
        "layout": "table",
        "group_painters": [],
        "painters": [],
        "browser_reload": 0,
        "num_columns": 1,
        "column_headers": "off",
        "sorters": [],
        "position": (1, 1),
        "size": (40, 20),
        "add_context_to_title": True,
        "sort_index": 0,
        "is_show_more": False,
    }
    base.update(overrides)  # type: ignore[typeddict-item]
    return base


@pytest.fixture(name="mock_dashlet_registry")
def fixture_mock_dashlet_registry() -> Iterator[MagicMock]:
    mock_registry = MagicMock()
    mock_dashlet_type = MagicMock()
    mock_dashlet_type.relative_layout_constraints.return_value.initial_size.to_tuple.return_value = (
        12,
        12,
    )
    mock_registry.__getitem__ = MagicMock(return_value=mock_dashlet_type)
    with patch("cmk.gui.dashboard.store.dashlet_registry", mock_registry):
        yield mock_registry


@pytest.fixture(name="mock_view_conversion")
def fixture_mock_view_conversion() -> Iterator[MagicMock]:
    with patch("cmk.gui.dashboard.store.internal_view_to_runtime_view") as mock:
        yield mock


@pytest.fixture(name="mock_embedded_view_conversion")
def fixture_mock_embedded_view_conversion() -> Iterator[MagicMock]:
    with patch("cmk.gui.dashboard.store._internal_embedded_view_to_runtime_embedded_view") as mock:
        yield mock


class TestMigrateDashboardConfigDefaults:
    def test_sets_defaults_for_missing_fields(self) -> None:
        dashboard = _make_dashboard()
        del dashboard["single_infos"]  # type: ignore[misc]
        del dashboard["context"]  # type: ignore[misc]
        del dashboard["mandatory_context_filters"]  # type: ignore[misc]
        del dashboard["widgets"]  # type: ignore[misc]

        result = migrate_dashboard_config(dashboard)

        assert result["single_infos"] == []
        assert result["context"] == {}
        assert result["mandatory_context_filters"] == []
        assert result["widgets"] == {}

    def test_preserves_existing_values(self) -> None:
        dashboard = _make_dashboard(
            single_infos=["host"],
            context={"host": {"host": "myhost"}},
            mandatory_context_filters=["host"],
            widgets={"w1": {"type": "hoststats", "position": (1, 1), "size": (30, 18)}},
        )

        result = migrate_dashboard_config(dashboard)

        assert result["single_infos"] == ["host"]
        assert result["context"] == {"host": {"host": "myhost"}}
        assert result["mandatory_context_filters"] == ["host"]
        assert result["widgets"] == {
            "w1": {"type": "hoststats", "position": (1, 1), "size": (30, 18)}
        }


class TestMigrateDashboardConfigDashletsToWidgets:
    def test_dashlets_converted_to_widgets_when_widgets_empty(self) -> None:
        dashlets = [
            {"type": "hoststats", "position": (1, 1), "size": (30, 18)},
            {"type": "servicestats", "position": (31, 1), "size": (30, 18)},
        ]
        dashboard = _make_dashboard(
            dashlets=dashlets,
            widgets={},
        )

        result = migrate_dashboard_config(dashboard)

        assert result["widgets"] == {
            "test_dashboard-0": {"type": "hoststats", "position": (1, 1), "size": (30, 18)},
            "test_dashboard-1": {"type": "servicestats", "position": (31, 1), "size": (30, 18)},
        }

    def test_dashlets_dropped_when_widgets_exist(self) -> None:
        existing_widgets = {
            "existing-widget": {"type": "hoststats", "position": (1, 1), "size": (30, 18)}
        }
        dashlets = [{"type": "servicestats", "position": (31, 1), "size": (30, 18)}]
        dashboard = _make_dashboard(
            dashlets=dashlets,
            widgets=existing_widgets.copy(),  # copy to check that it is not modified in-place
        )

        result = migrate_dashboard_config(dashboard)

        assert result["widgets"] == existing_widgets

    def test_dashlets_key_removed_after_migration(self) -> None:
        dashboard = _make_dashboard(
            dashlets=[{"type": "hoststats", "position": (1, 1), "size": (30, 18)}],
            widgets={},
        )

        result = migrate_dashboard_config(dashboard)

        assert "dashlets" not in result


class TestMigrateDashboardConfigRelativeGrid:
    def test_no_layout_key_triggers_widget_migration(
        self, mock_dashlet_registry: MagicMock
    ) -> None:
        dashboard = _make_dashboard(widgets={"w1": {"type": "hoststats", "position": (1, 1)}})
        # No "layout" key → defaults to relative_grid → _migrate_widgets runs
        assert "layout" not in dashboard

        result = migrate_dashboard_config(dashboard)

        assert "w1" in result["widgets"]
        assert "size" in result["widgets"]["w1"]  # check widget migration happened
        assert "embedded_views" in result

    def test_explicit_relative_grid_triggers_widget_migration(
        self, mock_dashlet_registry: MagicMock
    ) -> None:
        dashboard = _make_dashboard(
            widgets={"w1": {"type": "hoststats", "position": (1, 1)}},
            layout={"type": "relative_grid"},
        )

        result = migrate_dashboard_config(dashboard)

        assert "w1" in result["widgets"]
        assert "size" in result["widgets"]["w1"]  # check widget migration happened
        assert "embedded_views" in result

    def test_responsive_grid_skips_widget_migration(self) -> None:
        # NOTE: we won't actually have view widgets in a responsive grid layout,
        # this is just to test that the migration is skipped when the layout type is responsive_grid
        dashboard = _make_dashboard(
            widgets={"w1": _make_view_widget()},
            layout={"type": "responsive_grid", "layouts": {}},
        )

        result = migrate_dashboard_config(dashboard)

        # View widget should remain unchanged (not split into embedded_view)
        assert result["widgets"]["w1"]["type"] == "view"
        assert result["embedded_views"] == {}


class TestMigrateWidgetsSize:
    def test_widget_without_size_gets_default_from_registry(
        self, mock_dashlet_registry: MagicMock
    ) -> None:
        widget: StatsDashletConfig = {"type": "hoststats", "position": (1, 1)}
        assert "size" not in widget
        dashboard = _make_dashboard(widgets={"w1": widget})

        result = migrate_dashboard_config(dashboard)

        assert result["widgets"]["w1"]["size"] == (12, 12)

    def test_widget_with_existing_size_preserved(self, mock_dashlet_registry: MagicMock) -> None:
        widget: StatsDashletConfig = {"type": "hoststats", "position": (1, 1), "size": (30, 18)}
        dashboard = _make_dashboard(widgets={"w1": widget})

        result = migrate_dashboard_config(dashboard)

        assert result["widgets"]["w1"]["size"] == (30, 18)


class TestMigrateWidgetsViewWidget:
    def test_view_widget_converted_to_embedded_view(self, mock_dashlet_registry: MagicMock) -> None:
        view_widget = _make_view_widget()
        dashboard = _make_dashboard(widgets={"w1": view_widget})

        result = migrate_dashboard_config(dashboard)

        # Widget type should be changed to embedded_view
        assert result["widgets"]["w1"]["type"] == "embedded_view"
        embedded_view_name = result["widgets"]["w1"]["name"]  # type: ignore[typeddict-item]
        assert embedded_view_name == "test_view"
        assert result["widgets"]["w1"]["datasource"] == "hosts"  # type: ignore[typeddict-item]
        assert result["widgets"]["w1"]["position"] == (1, 1)
        assert result["widgets"]["w1"]["size"] == (40, 20)

        # Embedded view spec should contain the view definition
        assert embedded_view_name in result["embedded_views"]
        ev = result["embedded_views"][embedded_view_name]
        assert ev["datasource"] == "hosts"
        assert ev["layout"] == "table"
        assert ev["painters"] == []
        assert ev["group_painters"] == []
        assert ev["sorters"] == []
        assert ev["browser_reload"] == 0
        assert ev["num_columns"] == 1
        assert ev["column_headers"] == "off"
        assert ev["single_infos"] == ["host"]

    def test_view_widget_optional_fields_copied_when_present(
        self, mock_dashlet_registry: MagicMock
    ) -> None:
        view_widget = _make_view_widget(
            background=True,
            context={"host": {"host": "myhost"}},
            title="My View",
            show_title=True,
            add_headers="extra",
            mobile=True,
            mustsearch=True,
            force_checkboxes=True,
            user_sortable=True,
            play_sounds=True,
            inventory_join_macros={"macros": []},
        )
        dashboard = _make_dashboard(widgets={"w1": view_widget})

        result = migrate_dashboard_config(dashboard)

        w = result["widgets"]["w1"]
        assert w["background"] is True
        assert w["context"] == {"host": {"host": "myhost"}}
        assert w["title"] == "My View"
        assert w["show_title"] is True

        ev = result["embedded_views"]["test_view"]
        assert ev["add_headers"] == "extra"
        assert ev["mobile"] is True
        assert ev["mustsearch"] is True
        assert ev["force_checkboxes"] is True
        assert ev["user_sortable"] is True
        assert ev["play_sounds"] is True
        assert ev["inventory_join_macros"] == {"macros": []}

    def test_view_widget_optional_fields_absent_when_not_present(
        self, mock_dashlet_registry: MagicMock
    ) -> None:
        view_widget = _make_view_widget()
        dashboard = _make_dashboard(widgets={"w1": view_widget})

        result = migrate_dashboard_config(dashboard)

        w = result["widgets"]["w1"]
        assert "background" not in w
        assert "show_title" not in w

        ev = result["embedded_views"]["test_view"]
        assert "add_headers" not in ev
        assert "mobile" not in ev
        assert "mustsearch" not in ev
        assert "force_checkboxes" not in ev
        assert "user_sortable" not in ev
        assert "play_sounds" not in ev
        assert "inventory_join_macros" not in ev

    def test_existing_embedded_views_preserved(self, mock_dashlet_registry: MagicMock) -> None:
        existing_ev: DashboardEmbeddedViewSpec = {
            "single_infos": [],
            "datasource": "services",
            "layout": "table",
            "group_painters": [],
            "painters": [],
            "browser_reload": 30,
            "num_columns": 1,
            "column_headers": "off",
            "sorters": [],
        }
        view_widget = _make_view_widget(name="new_view")
        dashboard = _make_dashboard(
            widgets={"w1": view_widget},
            embedded_views={"old_view": existing_ev},
        )

        result = migrate_dashboard_config(dashboard)

        assert "old_view" in result["embedded_views"]
        assert "new_view" in result["embedded_views"]
        assert result["embedded_views"]["old_view"] == existing_ev


class TestInternalDashboardToRuntimeDashboard:
    def test_sets_defaults(
        self,
        mock_dashlet_registry: MagicMock,
        mock_view_conversion: MagicMock,
        mock_embedded_view_conversion: MagicMock,
    ) -> None:
        raw = dict(_make_dashboard())
        del raw["packaged"]
        del raw["main_menu_search_terms"]

        result = _internal_dashboard_to_runtime_dashboard(raw)

        assert result["packaged"] is False
        assert result["main_menu_search_terms"] == []

    def test_with_widgets_key_uses_widgets(
        self,
        mock_dashlet_registry: MagicMock,
        mock_view_conversion: MagicMock,
        mock_embedded_view_conversion: MagicMock,
    ) -> None:
        widget = {"type": "hoststats", "position": (1, 1), "size": (30, 18)}
        raw = _make_dashboard(widgets={"my-widget": widget})

        result = _internal_dashboard_to_runtime_dashboard(dict(raw))

        assert "my-widget" in result["widgets"]

    def test_with_dashlets_generates_widget_ids(
        self,
        mock_dashlet_registry: MagicMock,
        mock_view_conversion: MagicMock,
        mock_embedded_view_conversion: MagicMock,
    ) -> None:
        raw = dict(_make_dashboard())
        del raw["widgets"]
        raw["dashlets"] = [
            {"type": "hoststats", "position": (1, 1), "size": (30, 18)},
            {"type": "servicestats", "position": (31, 1), "size": (30, 18)},
        ]

        result = _internal_dashboard_to_runtime_dashboard(raw)

        assert "test_dashboard-0" in result["widgets"]
        assert "test_dashboard-1" in result["widgets"]
        assert "dashlets" not in result

    def test_view_widget_calls_internal_view_to_runtime_view(
        self,
        mock_dashlet_registry: MagicMock,
        mock_view_conversion: MagicMock,
        mock_embedded_view_conversion: MagicMock,
    ) -> None:
        view_widget = _make_view_widget()
        raw = _make_dashboard(widgets={"w1": view_widget})

        _internal_dashboard_to_runtime_dashboard(dict(raw))

        mock_view_conversion.assert_called_once_with(view_widget)

    def test_non_view_widget_not_transformed(
        self,
        mock_dashlet_registry: MagicMock,
        mock_view_conversion: MagicMock,
        mock_embedded_view_conversion: MagicMock,
    ) -> None:
        widget = {"type": "hoststats", "position": (1, 1), "size": (30, 18)}
        raw = _make_dashboard(widgets={"w1": widget})

        result = _internal_dashboard_to_runtime_dashboard(dict(raw))

        mock_view_conversion.assert_not_called()
        assert result["widgets"]["w1"]["type"] == "hoststats"

    def test_embedded_views_converted(
        self, mock_dashlet_registry: MagicMock, mock_view_conversion: MagicMock
    ) -> None:
        raw_ev: DashboardEmbeddedViewSpec = {
            "single_infos": [],
            "datasource": "hosts",
            "layout": "table",
            "group_painters": [],
            "painters": [],
            "browser_reload": 0,
            "num_columns": 1,
            "column_headers": "off",
            "sorters": [],
        }
        raw = _make_dashboard(
            embedded_views={"ev1": raw_ev},
            layout={"type": "responsive_grid", "layouts": {}},
        )

        with patch(
            "cmk.gui.dashboard.store._internal_embedded_view_to_runtime_embedded_view",
            side_effect=lambda x: {**x, "converted": True},
        ):
            result = _internal_dashboard_to_runtime_dashboard(dict(raw))

        # converted is a marker we added in the side_effect to check that the conversion was applied
        assert result["embedded_views"]["ev1"]["converted"] is True  # type: ignore[typeddict-item]

    def test_no_embedded_views_gives_empty_dict(
        self,
        mock_dashlet_registry: MagicMock,
        mock_view_conversion: MagicMock,
        mock_embedded_view_conversion: MagicMock,
    ) -> None:
        raw = _make_dashboard(
            embedded_views={},
            layout={"type": "responsive_grid", "layouts": {}},
        )

        result = _internal_dashboard_to_runtime_dashboard(dict(raw))

        assert result["embedded_views"] == {}

    def test_dashlets_key_removed_from_output(
        self,
        mock_dashlet_registry: MagicMock,
        mock_view_conversion: MagicMock,
        mock_embedded_view_conversion: MagicMock,
    ) -> None:
        raw = dict(_make_dashboard())
        raw["dashlets"] = [{"type": "hoststats", "position": (1, 1), "size": (30, 18)}]
        del raw["widgets"]

        result = _internal_dashboard_to_runtime_dashboard(raw)

        assert "dashlets" not in result
