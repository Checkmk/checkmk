#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Shared helpers for dashboard API tests across editions."""

from collections.abc import Mapping

import pytest

from cmk.livestatus_client.testing import MockLiveStatusConnection
from tests.testlib.rest_api_client import ClientRegistry


def create_dashboard_payload(
    dashboard_id: str,
    widgets: Mapping[str, Mapping[str, object]],
    icon_config: Mapping[str, object] | None = None,
) -> dict[str, object]:
    menu: dict[str, object] = {
        "topic": "overview",
        "sort_index": 99,
        "search_terms": [],
        "is_show_more": False,
    }
    if icon_config is not None:
        menu["icon"] = icon_config
    return {
        "id": dashboard_id,
        "general_settings": {
            "title": {"text": "Test Dashboard", "render": True, "include_context": False},
            "description": "This is a test dashboard",
            "menu": menu,
            "visibility": {
                "hide_in_monitor_menu": False,
                "hide_in_drop_down_menus": False,
                "share": "no",
            },
        },
        "filter_context": {
            "restricted_to_single": [],
            "filters": {},
            "mandatory_context_filters": [],
        },
        "widgets": widgets,
        "layout": {"type": "relative_grid"},
    }


def create_widget(content: dict[str, object]) -> dict[str, object]:
    return {
        "layout": {
            "type": "relative_grid",
            "position": {"x": 1, "y": 1},
            "size": {"width": 10, "height": 10},
        },
        "general_settings": {
            "title": {"text": "Test Widget", "render_mode": "with_background"},
            "render_background": True,
        },
        "content": content,
        "filters": {},
    }


def check_widget_create(
    clients: ClientRegistry,
    content: dict[str, object],
) -> None:
    expected_type = content["type"]
    resp = clients.DashboardClient.create_relative_grid_dashboard(
        create_dashboard_payload(
            "test_dashboard",
            {"test_widget": create_widget(content)},
        )
    )
    assert resp.status_code == 201, f"Expected 201, got {resp.status_code} {resp.body!r}"
    widgets = resp.json["extensions"]["widgets"]
    widget = next(iter(widgets.values()))  # IDs are not consistent
    assert widget["content"]["type"] == expected_type


# ---------------------------------------------------------------------------
# Edition-sensitive test classes (used by per-edition test files)
# ---------------------------------------------------------------------------


class TestProblemGraphContent:
    def test_create(
        self, clients: ClientRegistry, mock_livestatus: MockLiveStatusConnection
    ) -> None:
        # NOTE: `mock_livestatus` is used, because graph widgets want the connected site PIDs.
        # No queries are actually executed.
        check_widget_create(
            clients,
            {
                "type": "problem_graph",
                "timerange": {"type": "predefined", "value": "last_25_hours"},
                "graph_render_options": {"show_legend": False},
            },
        )


class TestCombinedGraphContent:
    def test_create(
        self, clients: ClientRegistry, mock_livestatus: MockLiveStatusConnection
    ) -> None:
        # NOTE: `mock_livestatus` is used, because graph widgets want the connected site PIDs.
        # No queries are actually executed.
        check_widget_create(
            clients,
            {
                "type": "combined_graph",
                "timerange": {"type": "predefined", "value": "last_25_hours"},
                "graph_render_options": {},
                "graph_template": "disk_utilization",
                "presentation": "lines",
            },
        )


class TestSingleTimeseriesContent:
    def test_create(
        self, clients: ClientRegistry, mock_livestatus: MockLiveStatusConnection
    ) -> None:
        # NOTE: `mock_livestatus` is used, because graph widgets want the connected site PIDs.
        # No queries are actually executed.
        check_widget_create(
            clients,
            {
                "type": "single_timeseries",
                "timerange": {"type": "predefined", "value": "last_25_hours"},
                "graph_render_options": {},
                "metric": "availability",
                "color": "#ABCDEF",
            },
        )


class TestCustomGraphContent:
    def test_create(self, clients: ClientRegistry) -> None:
        check_widget_create(
            clients,
            {
                "type": "custom_graph",
                "timerange": {"type": "predefined", "value": "last_25_hours"},
                "graph_render_options": {},
                "custom_graph": "???",
            },
        )


class TestBarplotContent:
    def test_create(self, clients: ClientRegistry) -> None:
        check_widget_create(
            clients,
            {
                "type": "barplot",
                "metric": "availability",
                "display_range": "automatic",
            },
        )


class TestGaugeContent:
    def test_create(self, clients: ClientRegistry) -> None:
        check_widget_create(
            clients,
            {
                "type": "gauge",
                "metric": "availability",
                "display_range": {
                    "type": "fixed",
                    "unit": "%",
                    "minimum": 0,
                    "maximum": 100,
                },
                "time_range": "current",
                "status_display": {"type": "text", "for_states": "not_ok"},
            },
        )


class TestSingleMetricContent:
    def test_create(self, clients: ClientRegistry) -> None:
        check_widget_create(
            clients,
            {
                "type": "single_metric",
                "metric": "availability",
                "time_range": {
                    "type": "window",
                    "window": {"type": "predefined", "value": "last_25_hours"},
                    "consolidation": "maximum",
                },
                "status_display": {"type": "text", "for_states": "not_ok"},
                "display_range": "automatic",
                "show_display_range_limits": False,
            },
        )


class TestAverageScatterplotContent:
    def test_create(self, clients: ClientRegistry) -> None:
        check_widget_create(
            clients,
            {
                "type": "average_scatterplot",
                "time_range": {"type": "predefined", "value": "last_25_hours"},
                "metric": "availability",
                "metric_color": "#ABCDEF",
                "average_color": "default",
                "median_color": "default",
            },
        )


class TestTopListContent:
    def test_create(self, clients: ClientRegistry) -> None:
        check_widget_create(
            clients,
            {
                "type": "top_list",
                "metric": "availability",
                "display_range": "automatic",
                "columns": {
                    "show_service_description": True,
                    "show_bar_visualization": True,
                },
                "ranking_order": "high",
                "limit_to": 10,
            },
        )


@pytest.mark.parametrize("widget_type", ["host_state", "service_state"])
class TestStateContent:
    def test_create(self, clients: ClientRegistry, widget_type: str) -> None:
        check_widget_create(
            clients,
            {
                "type": widget_type,
                "status_display": {"type": "background", "for_states": "not_ok"},
                "show_summary": "not_ok",
            },
        )


class TestHostStateSummaryContent:
    def test_create(self, clients: ClientRegistry) -> None:
        check_widget_create(
            clients,
            {
                "type": "host_state_summary",
                "state": "UP",
            },
        )


class TestServiceStateSummaryContent:
    def test_create(self, clients: ClientRegistry) -> None:
        check_widget_create(
            clients,
            {
                "type": "service_state_summary",
                "state": "OK",
            },
        )


class TestInventoryContent:
    def test_create(self, clients: ClientRegistry) -> None:
        check_widget_create(
            clients,
            {
                "type": "inventory",
                "path": "hardware.cpu.cores",
            },
        )

    def test_compute_widget_attributes(self, clients: ClientRegistry) -> None:
        resp = clients.DashboardClient.compute_widget_attributes(
            {
                "type": "inventory",
                "path": "hardware.cpu.cores",
            }
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code} {resp.body!r}"
        assert resp.json["value"]["filter_context"]["uses_infos"] == ["host"]

    def test_compute_widget_titles(self, clients: ClientRegistry) -> None:
        resp = clients.DashboardClient.compute_widget_titles(
            {
                "id": {
                    "general_settings": {
                        "title": {
                            "text": "$DEFAULT_TITLE$: custom",
                            "render_mode": "with_background",
                        },
                        "render_background": True,
                    },
                    "content": {
                        "type": "inventory",
                        "path": "hardware.cpu.cores",
                    },
                    "filters": {},
                },
            }
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code} {resp.body!r}"
        titles = resp.json["extensions"]["titles"]
        assert titles["id"] == "Processor \u27a4 #Cores: custom"


class TestAlertOverviewContent:
    def test_create(self, clients: ClientRegistry) -> None:
        check_widget_create(
            clients,
            {
                "type": "alert_overview",
                "time_range": {"type": "predefined", "value": "last_25_hours"},
                "limit_objects": 10,
            },
        )


class TestSiteOverviewContent:
    def test_create(self, clients: ClientRegistry) -> None:
        check_widget_create(
            clients,
            {
                "type": "site_overview",
                "dataset": "sites",
                "hexagon_size": "default",
            },
        )


@pytest.mark.parametrize("widget_type", ["alert_timeline", "notification_timeline"])
class TestTimelineContent:
    def test_create(self, clients: ClientRegistry, widget_type: str) -> None:
        check_widget_create(
            clients,
            {
                "type": widget_type,
                "render_mode": {
                    "type": "bar_chart",
                    "time_range": {"type": "predefined", "value": "last_25_hours"},
                    "time_resolution": "hour",
                },
                "log_target": "both",
            },
        )


@pytest.mark.parametrize("widget_type", ["ntop_alerts", "ntop_flows", "ntop_top_talkers"])
class TestNtopContent:
    def test_create(self, clients: ClientRegistry, widget_type: str) -> None:
        check_widget_create(
            clients,
            {"type": widget_type},
        )
