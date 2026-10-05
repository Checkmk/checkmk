#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Shared helpers for dashboard API tests across editions."""

import datetime as dt
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from http import HTTPStatus

import pytest

from cmk.ccc.user import UserId
from tests.testlib.unit.rest_api_client import ClientRegistry


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


@dataclass(frozen=True)
class SavedWidget:
    source: dict[str, object]
    headers: dict[str, str]


@contextmanager
def dashboard_widget_token(
    clients: ClientRegistry, owner: UserId, content: dict[str, object]
) -> Iterator[SavedWidget]:
    """A dashboard with one widget and a token for it, as a saved-arm request needs them."""
    dashboard_id = "token_dashboard"
    created = clients.DashboardClient.create_relative_grid_dashboard(
        create_dashboard_payload(dashboard_id, {"widget": create_widget(content)})
    )
    token = clients.DashboardClient.create_dashboard_token(
        {
            "dashboard_owner": owner,
            "dashboard_id": dashboard_id,
            "comment": "Widget token",
            "expires_at": (dt.datetime.now(dt.UTC) + dt.timedelta(days=1)).isoformat(),
        }
    )
    try:
        yield SavedWidget(
            source={
                "type": "saved",
                "widget_id": next(iter(created.json["extensions"]["widgets"])),
            },
            headers={"Authorization": f"CMK-TOKEN 0:{token.json['id']}"},
        )
    finally:
        clients.DashboardClient.delete(dashboard_id)


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
    assert resp.status_code == HTTPStatus.CREATED, (
        f"Expected 201, got {resp.status_code} {resp.body!r}"
    )
    widgets = resp.json["extensions"]["widgets"]
    widget = next(iter(widgets.values()))  # IDs are not consistent
    assert widget["content"]["type"] == expected_type


# ---------------------------------------------------------------------------
# Edition-sensitive test classes (used by per-edition test files)
# ---------------------------------------------------------------------------


class TestProblemGraphContent:
    @pytest.mark.usefixtures("mock_livestatus")
    def test_create(self, clients: ClientRegistry) -> None:
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
    @pytest.mark.usefixtures("mock_livestatus")
    def test_create(self, clients: ClientRegistry) -> None:
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
    @pytest.mark.usefixtures("mock_livestatus")
    def test_create(self, clients: ClientRegistry) -> None:
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
                "spark_height_mode": "full",
                "show_delta": True,
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
                "contextual_link": {"type": "none"},
            },
        )

    def test_a_none_link_round_trips(self, clients: ClientRegistry) -> None:
        clients.DashboardClient.create_relative_grid_dashboard(
            create_dashboard_payload(
                "top_list_dashboard",
                {
                    "top_list": create_widget(
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
                            "contextual_link": {"type": "none"},
                        }
                    )
                },
            )
        )

        widgets = clients.DashboardClient.get_relative_grid_dashboard("top_list_dashboard").json[
            "extensions"
        ]["widgets"]
        assert next(iter(widgets.values()))["content"]["contextual_link"] == {"type": "none"}


@pytest.mark.parametrize("widget_type", ["host_state", "service_state"])
class TestStateContent:
    def test_create(self, clients: ClientRegistry, widget_type: str) -> None:
        check_widget_create(
            clients,
            {
                "type": widget_type,
                "status_display": {"type": "background", "for_states": "not_ok"},
                "show_summary": "not_ok",
                "contextual_link": {"type": "default"},
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
                "contextual_link": {"type": "default"},
            },
        )

    def test_compute_widget_attributes(self, clients: ClientRegistry) -> None:
        resp = clients.DashboardClient.compute_widget_attributes(
            {
                "type": "inventory",
                "path": "hardware.cpu.cores",
                "contextual_link": {"type": "default"},
            }
        )
        assert resp.status_code == HTTPStatus.OK, (
            f"Expected 200, got {resp.status_code} {resp.body!r}"
        )
        assert resp.json["value"]["filter_context"]["uses_infos"] == ["host"]

    def test_an_inherited_link_round_trips(self, clients: ClientRegistry) -> None:
        link = {
            "type": "inherited",
            "location": {"type": "dashboards", "name": "main", "owner": None},
            "include_context": False,
            "include_time_range": False,
            "show_filter_form": False,
        }
        clients.DashboardClient.create_relative_grid_dashboard(
            create_dashboard_payload(
                "inventory_dashboard",
                {
                    "inventory": create_widget(
                        {"type": "inventory", "path": "hardware.cpu.cores", "contextual_link": link}
                    )
                },
            )
        )

        widgets = clients.DashboardClient.get_relative_grid_dashboard("inventory_dashboard").json[
            "extensions"
        ]["widgets"]
        assert next(iter(widgets.values()))["content"]["contextual_link"] == link

    def test_an_explicit_default_reads_back_as_default(self, clients: ClientRegistry) -> None:
        clients.DashboardClient.create_relative_grid_dashboard(
            create_dashboard_payload(
                "inventory_dashboard",
                {
                    "inventory": create_widget(
                        {
                            "type": "inventory",
                            "path": "hardware.cpu.cores",
                            "contextual_link": {"type": "default"},
                        }
                    )
                },
            )
        )

        widgets = clients.DashboardClient.get_relative_grid_dashboard("inventory_dashboard").json[
            "extensions"
        ]["widgets"]
        assert next(iter(widgets.values()))["content"]["contextual_link"] == {"type": "default"}


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
                "contextual_link": {"type": "default"},
            },
        )

    def test_an_inherited_link_round_trips(self, clients: ClientRegistry) -> None:
        link = {
            "type": "inherited",
            "location": {"type": "dashboards", "name": "main", "owner": None},
            "include_context": True,
            "include_time_range": False,
            "show_filter_form": False,
        }
        clients.DashboardClient.create_relative_grid_dashboard(
            create_dashboard_payload(
                "site_overview_dashboard",
                {
                    "site_overview": create_widget(
                        {
                            "type": "site_overview",
                            "dataset": "sites",
                            "hexagon_size": "default",
                            "contextual_link": link,
                        }
                    )
                },
            )
        )

        widgets = clients.DashboardClient.get_relative_grid_dashboard(
            "site_overview_dashboard"
        ).json["extensions"]["widgets"]
        assert next(iter(widgets.values()))["content"]["contextual_link"] == link

    def test_an_explicit_default_reads_back_as_default(self, clients: ClientRegistry) -> None:
        clients.DashboardClient.create_relative_grid_dashboard(
            create_dashboard_payload(
                "site_overview_dashboard",
                {
                    "site_overview": create_widget(
                        {
                            "type": "site_overview",
                            "dataset": "sites",
                            "hexagon_size": "default",
                            "contextual_link": {"type": "default"},
                        }
                    )
                },
            )
        )

        widgets = clients.DashboardClient.get_relative_grid_dashboard(
            "site_overview_dashboard"
        ).json["extensions"]["widgets"]
        assert next(iter(widgets.values()))["content"]["contextual_link"] == {"type": "default"}


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

    @pytest.mark.parametrize(
        "render_mode",
        [
            {"type": "bar_chart", "time_range": "dashboard", "time_resolution": "day"},
            {"type": "simple_number", "time_range": "dashboard"},
        ],
    )
    def test_a_window_that_follows_the_dashboard_round_trips(
        self, clients: ClientRegistry, widget_type: str, render_mode: dict[str, str]
    ) -> None:
        resp = clients.DashboardClient.create_relative_grid_dashboard(
            create_dashboard_payload(
                "timeline_dashboard",
                {
                    "timeline": create_widget(
                        {"type": widget_type, "render_mode": render_mode, "log_target": "host"}
                    )
                },
            )
        )

        widgets = resp.json["extensions"]["widgets"]
        assert next(iter(widgets.values()))["content"]["render_mode"] == render_mode


@pytest.mark.parametrize("widget_type", ["ntop_alerts", "ntop_flows", "ntop_top_talkers"])
class TestNtopContent:
    def test_create(self, clients: ClientRegistry, widget_type: str) -> None:
        check_widget_create(
            clients,
            {"type": widget_type},
        )
