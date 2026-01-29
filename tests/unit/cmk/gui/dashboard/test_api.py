#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import get_args, get_type_hints

import pytest

from cmk.ccc.user import UserId
from cmk.gui.dashboard import get_all_dashboards
from cmk.gui.dashboard.api._utils import INTERNAL_TO_API_TYPE_NAME
from cmk.gui.dashboard.api.model.constants import RESPONSIVE_GRID_BREAKPOINTS
from cmk.gui.dashboard.api.model.widget_content import _CONTENT_TYPES
from cmk.gui.dashboard.api.model.widget_content._base import BaseWidgetContent
from cmk.gui.type_defs import ColumnSpec, DashboardEmbeddedViewSpec, SorterSpec, VisualLinkSpec
from cmk.gui.views.icon.registry import all_icons
from cmk.livestatus_client.testing import MockLiveStatusConnection
from tests.testlib.common.repo import (
    is_cloud_repo,
    is_pro_repo,
    is_ultimate_repo,
    is_ultimatemt_repo,
)
from tests.testlib.unit.rest_api_client import ClientRegistry


@pytest.mark.parametrize("widget_api_model", _CONTENT_TYPES)
def test_widget_api_model_has_valid_type_mapping(widget_api_model: BaseWidgetContent) -> None:
    literal_values = get_args(get_type_hints(widget_api_model)["type"])

    api_widget_type_name = literal_values[0] if literal_values else None
    internal_widget_type_name = widget_api_model.internal_type()
    mapped_api_type_name = INTERNAL_TO_API_TYPE_NAME.get(internal_widget_type_name)

    assert len(literal_values) == 1, "Widget content model should have exactly one Literal value"

    assert internal_widget_type_name in INTERNAL_TO_API_TYPE_NAME, (
        f"Internal widget type '{internal_widget_type_name}' not found in INTERNAL_TO_API_TYPE_NAME mapping. "
        f"INTERNAL_TO_API_TYPE_NAME must contain all internal widget types."
    )

    assert mapped_api_type_name == api_widget_type_name, (
        f"Mismatch between internal type '{internal_widget_type_name}' and API type '{api_widget_type_name}'. "
        f"INTERNAL_TO_API_TYPE must map '{internal_widget_type_name}' to '{api_widget_type_name}'. "
    )


def test_show_dashboard_constants(clients: ClientRegistry) -> None:
    resp = clients.ConstantClient.get_dashboard()

    assert resp.status_code == 200, f"Expected 200, got {resp.status_code} {resp.body!r}"
    assert len(resp.json["extensions"]["widgets"]) > 0, (
        "Expected at least one widget to be returned"
    )
    assert set(list(resp.json["extensions"]["widgets"].values())[0]) == {"layout", "filter_context"}
    assert (
        resp.json["extensions"]["responsive_grid_breakpoints"].keys()
        == RESPONSIVE_GRID_BREAKPOINTS.keys()
    ), "Expected all and only the configured breakpoints to be returned"
    for breakpoint_id, config in RESPONSIVE_GRID_BREAKPOINTS.items():
        response_config = resp.json["extensions"]["responsive_grid_breakpoints"][breakpoint_id]
        assert response_config["min_width"] == config["min_width"], (
            "Expected min width response to match the internal one"
        )
        assert response_config["columns"] == config["columns"], (
            "Expected columns response to match the internal one"
        )


def test_show_dashboard(clients: ClientRegistry, mock_livestatus: MockLiveStatusConnection) -> None:
    # NOTE: `mock_livestatus` is used, because graph widgets want the connected site PIDs.
    # No queries are actually executed.

    # main builtin dashboard should always be present
    resp = clients.DashboardClient.get_relative_grid_dashboard("main")
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code} {resp.body!r}"
    # check that we got the correct dashboard
    assert resp.json["id"] == "main", "Expected dashboard ID to be 'main'"


def test_show_non_existent_dashboard(clients: ClientRegistry) -> None:
    resp = clients.DashboardClient.get_relative_grid_dashboard("non_existent" * 4, expect_ok=False)
    assert resp.status_code == 404, f"Expected 404, got {resp.status_code} {resp.body!r}"


def _create_dashboard_payload(
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


def _create_widget(content: dict[str, object]) -> dict[str, object]:
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


def test_create_empty_dashboard(clients: ClientRegistry) -> None:
    resp = clients.DashboardClient.create_relative_grid_dashboard(
        _create_dashboard_payload("test_dashboard", {})
    )
    assert resp.status_code == 201, f"Expected 201, got {resp.status_code} {resp.body!r}"
    assert resp.json["id"] == "test_dashboard", (
        "Expected created dashboard ID to be 'test_dashboard'"
    )
    assert resp.json["extensions"]["widgets"] == {}, "Expected no widgets"


def test_clone_relative_dashboard(clients: ClientRegistry) -> None:
    _resp = clients.DashboardClient.create_relative_grid_dashboard(
        _create_dashboard_payload("test_dashboard", {})
    )
    resp = clients.DashboardClient.clone_as_relative_grid_dashboard(
        {"reference_dashboard_id": "test_dashboard", "dashboard_id": "clone_dashboard"}
    )
    assert resp.status_code == 201, f"Expected 201, got {resp.status_code}"
    assert resp.json["id"] == "clone_dashboard", (
        "Expected cloned dashboard ID to be 'clone_dashboard'"
    )


def test_edit_relative_grid_layout(clients: ClientRegistry) -> None:
    dashboard_id = "test_dashboard"
    new_dashboard_id = "some_other_id"
    clients.DashboardClient.create_relative_grid_dashboard(
        _create_dashboard_payload(dashboard_id, {})
    )
    resp = clients.DashboardClient.edit_relative_grid_dashboard(
        dashboard_id,
        _create_dashboard_payload(new_dashboard_id, {}),
    )
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code} {resp.body!r}"
    assert resp.json["id"] == new_dashboard_id


def test_edit_id_in_use(clients: ClientRegistry) -> None:
    dashboard_1 = "test_dashboard_1"
    dashboard_2 = "test_dashboard_2"
    for dashboard_id in (dashboard_1, dashboard_2):
        clients.DashboardClient.create_relative_grid_dashboard(
            _create_dashboard_payload(dashboard_id, {})
        )
    resp = clients.DashboardClient.edit_relative_grid_dashboard(
        dashboard_1,
        _create_dashboard_payload(dashboard_2, {}),
        expect_ok=False,
    )
    assert resp.status_code == 400, f"Expected 400, got {resp.status_code} {resp.body!r}"
    assert resp.json["title"] == "Dashboard ID already in use"


@pytest.mark.parametrize(
    "dashboard_id", [pytest.param("", id="empty"), "with whitespace", "with_special_chars!!!"]
)
def test_create_dashboard_with_invalid_id(clients: ClientRegistry, dashboard_id: str) -> None:
    resp = clients.DashboardClient.create_relative_grid_dashboard(
        _create_dashboard_payload(dashboard_id, {}), expect_ok=False
    )
    assert resp.status_code == 400, f"Expected 400, got {resp.status_code} {resp.body!r}"
    assert resp.json["fields"]["body.id"]["msg"] == "String should match pattern '^[a-zA-Z0-9_]+$'"


def test_create_dashboard_with_invalid_widget_type(clients: ClientRegistry) -> None:
    payload = _create_dashboard_payload(
        "invalid_widget_type",
        {"test_widget": _create_widget({"type": "not_a_real_type"})},
    )
    resp = clients.DashboardClient.create_relative_grid_dashboard(payload, expect_ok=False)
    assert resp.status_code == 400, f"Expected 400, got {resp.status_code} {resp.body!r}"


def test_delete_dashboard(clients: ClientRegistry) -> None:
    dashboard_id = "to_delete"
    clients.DashboardClient.create_relative_grid_dashboard(
        _create_dashboard_payload(dashboard_id, {})
    )

    resp = clients.DashboardClient.delete(dashboard_id)
    assert resp.status_code == 204, f"Expected 204, got {resp.status_code} {resp.body!r}"
    resp = clients.DashboardClient.get_relative_grid_dashboard(dashboard_id, expect_ok=False)
    assert resp.status_code == 404, f"Expected 404, got {resp.status_code} {resp.body!r}"


def test_compute_widget_titles(clients: ClientRegistry) -> None:
    resp = clients.DashboardClient.compute_widget_titles(
        {
            "widget-1": {
                "general_settings": {
                    "title": {"text": "Widget 1", "render_mode": "with_background"},
                    "render_background": True,
                },
                "content": {
                    "type": "static_text",
                    "text": "This is a static text widget",
                },
                "filters": {},
            },
            "widget-2": {
                "general_settings": {
                    "title": {"text": "$DEFAULT_TITLE$: custom", "render_mode": "with_background"},
                    "render_background": True,
                },
                "content": {
                    "type": "performance_graph",
                    "timerange": {"type": "predefined", "value": "last_25_hours"},
                    "graph_render_options": {},
                    "source": "active_sessions",
                },
                "filters": {},
            },
        }
    )
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code} {resp.body!r}"
    titles = resp.json["extensions"]["titles"]
    assert titles["widget-1"] == "Widget 1", "Expected title for widget-1 to be 'Widget 1'"
    assert titles["widget-2"] == "Time series graph: custom"


class TestDashboardMetadata:
    def test_list_dashboard_metadata(self, clients: ClientRegistry) -> None:
        resp = clients.DashboardClient.list_dashboard_metadata()

        assert resp.status_code == 200, f"Expected 200, got {resp.status_code} {resp.body!r}"
        assert len(resp.json["value"]) > 0, "Expected at least one dashboard to be returned"

    def test_show_dashboard_metadata(self, clients: ClientRegistry) -> None:
        resp = clients.DashboardClient.show_dashboard_metadata("main", owner="")

        assert resp.status_code == 200, f"Expected 200, got {resp.status_code} {resp.body!r}"


class TestDashboardIcon:
    def test_create_with_icon(self, clients: ClientRegistry) -> None:
        # use a random icon name, the list of available icons may change depending on editions
        icons = list(all_icons())
        icon_config = {"name": icons[0]}

        resp = clients.DashboardClient.create_relative_grid_dashboard(
            _create_dashboard_payload("test_dashboard_with_icon", {}, icon_config=icon_config)
        )
        assert resp.status_code == 201, f"Expected 201, got {resp.status_code} {resp.body!r}"
        assert resp.json["extensions"]["general_settings"]["menu"]["icon"] == icon_config, (
            "Expected icon to be set"
        )

    def test_create_with_icon_with_emblem(self, clients: ClientRegistry) -> None:
        # use a random icon name, the list of available icons may change depending on editions
        icons = list(all_icons())
        icon_config = {"name": icons[0], "emblem": icons[-1]}

        resp = clients.DashboardClient.create_relative_grid_dashboard(
            _create_dashboard_payload("test_dashboard_with_icon", {}, icon_config=icon_config)
        )
        assert resp.status_code == 201, f"Expected 201, got {resp.status_code} {resp.body!r}"
        assert resp.json["extensions"]["general_settings"]["menu"]["icon"] == icon_config, (
            "Expected icon to be set"
        )


def _check_widget_create(
    clients: ClientRegistry,
    content: dict[str, object],
) -> None:
    expected_type = content["type"]
    resp = clients.DashboardClient.create_relative_grid_dashboard(
        _create_dashboard_payload(
            "test_dashboard",
            {"test_widget": _create_widget(content)},
        )
    )
    assert resp.status_code == 201, f"Expected 201, got {resp.status_code} {resp.body!r}"
    widgets = resp.json["extensions"]["widgets"]
    widget = next(iter(widgets.values()))  # IDs are not consistent
    assert widget["content"]["type"] == expected_type


@pytest.fixture(name="skip_in_raw_edition", scope="session")
def fixture_skip_in_raw_edition() -> None:
    if is_cloud_repo() or is_ultimate_repo() or is_ultimatemt_repo() or is_pro_repo():
        return

    pytest.skip("This test is not applicable for the raw edition.")


@pytest.mark.usefixtures("skip_in_raw_edition")
class TestProblemGraphContent:
    def test_create(
        self, clients: ClientRegistry, mock_livestatus: MockLiveStatusConnection
    ) -> None:
        # NOTE: `mock_livestatus` is used, because graph widgets want the connected site PIDs.
        # No queries are actually executed.
        _check_widget_create(
            clients,
            {
                "type": "problem_graph",
                "timerange": {"type": "predefined", "value": "last_25_hours"},
                "graph_render_options": {"show_legend": False},
            },
        )


@pytest.mark.usefixtures("skip_in_raw_edition")
class TestCombinedGraphContent:
    def test_create(
        self, clients: ClientRegistry, mock_livestatus: MockLiveStatusConnection
    ) -> None:
        # NOTE: `mock_livestatus` is used, because graph widgets want the connected site PIDs.
        # No queries are actually executed.
        _check_widget_create(
            clients,
            {
                "type": "combined_graph",
                "timerange": {"type": "predefined", "value": "last_25_hours"},
                "graph_render_options": {},
                "graph_template": "disk_utilization",
                "presentation": "lines",
            },
        )


@pytest.mark.usefixtures("skip_in_raw_edition")
class TestSingleTimeseriesContent:
    def test_create(
        self, clients: ClientRegistry, mock_livestatus: MockLiveStatusConnection
    ) -> None:
        # NOTE: `mock_livestatus` is used, because graph widgets want the connected site PIDs.
        # No queries are actually executed.
        _check_widget_create(
            clients,
            {
                "type": "single_timeseries",
                "timerange": {"type": "predefined", "value": "last_25_hours"},
                "graph_render_options": {},
                "metric": "availability",
                "color": "#ABCDEF",
            },
        )


@pytest.mark.usefixtures("skip_in_raw_edition")
class TestCustomGraphContent:
    def test_create(self, clients: ClientRegistry) -> None:
        _check_widget_create(
            clients,
            {
                "type": "custom_graph",
                "timerange": {"type": "predefined", "value": "last_25_hours"},
                "graph_render_options": {},
                "custom_graph": "???",
            },
        )


class TestPerformanceGraphContent:
    def test_create(self, clients: ClientRegistry) -> None:
        _check_widget_create(
            clients,
            {
                "type": "performance_graph",
                "timerange": {"type": "predefined", "value": "last_25_hours"},
                "graph_render_options": {},
                "source": "active_sessions",
            },
        )


@pytest.mark.usefixtures("skip_in_raw_edition")
class TestBarplotContent:
    def test_create(self, clients: ClientRegistry) -> None:
        _check_widget_create(
            clients,
            {
                "type": "barplot",
                "metric": "availability",
                "display_range": "automatic",
            },
        )


@pytest.mark.usefixtures("skip_in_raw_edition")
class TestGaugeContent:
    def test_create(self, clients: ClientRegistry) -> None:
        _check_widget_create(
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


@pytest.mark.usefixtures("skip_in_raw_edition")
class TestSingleMetricContent:
    def test_create(self, clients: ClientRegistry) -> None:
        _check_widget_create(
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


@pytest.mark.usefixtures("skip_in_raw_edition")
class TestAverageScatterplotContent:
    def test_create(self, clients: ClientRegistry) -> None:
        _check_widget_create(
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


@pytest.mark.usefixtures("skip_in_raw_edition")
class TestTopListContent:
    def test_create(self, clients: ClientRegistry) -> None:
        _check_widget_create(
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


@pytest.mark.usefixtures("skip_in_raw_edition")
@pytest.mark.parametrize("widget_type", ["host_state", "service_state"])
class TestStateContent:
    def test_create(self, clients: ClientRegistry, widget_type: str) -> None:
        _check_widget_create(
            clients,
            {
                "type": widget_type,
                "status_display": {"type": "background", "for_states": "not_ok"},
                "show_summary": "not_ok",
            },
        )


@pytest.mark.usefixtures("skip_in_raw_edition")
class TestHostStateSummaryContent:
    def test_create(self, clients: ClientRegistry) -> None:
        _check_widget_create(
            clients,
            {
                "type": "host_state_summary",
                "state": "UP",
            },
        )


@pytest.mark.usefixtures("skip_in_raw_edition")
class TestServiceStateSummaryContent:
    def test_create(self, clients: ClientRegistry) -> None:
        _check_widget_create(
            clients,
            {
                "type": "service_state_summary",
                "state": "OK",
            },
        )


@pytest.mark.usefixtures("skip_in_raw_edition")
class TestInventoryContent:
    def test_create(self, clients: ClientRegistry) -> None:
        _check_widget_create(
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
        assert titles["id"] == "Processor ➤ #Cores: custom"


@pytest.mark.usefixtures("skip_in_raw_edition")
class TestAlertOverviewContent:
    def test_create(self, clients: ClientRegistry) -> None:
        _check_widget_create(
            clients,
            {
                "type": "alert_overview",
                "time_range": {"type": "predefined", "value": "last_25_hours"},
                "limit_objects": 10,
            },
        )


@pytest.mark.usefixtures("skip_in_raw_edition")
class TestSiteOverviewContent:
    def test_create(self, clients: ClientRegistry) -> None:
        _check_widget_create(
            clients,
            {
                "type": "site_overview",
                "dataset": "sites",
                "hexagon_size": "default",
            },
        )


@pytest.mark.parametrize("widget_type", ["host_stats", "service_stats", "event_stats"])
class TestStatsContent:
    def test_create(self, clients: ClientRegistry, widget_type: str) -> None:
        _check_widget_create(
            clients,
            {
                "type": widget_type,
            },
        )


@pytest.mark.usefixtures("skip_in_raw_edition")
@pytest.mark.parametrize("widget_type", ["alert_timeline", "notification_timeline"])
class TestTimelineContent:
    def test_create(self, clients: ClientRegistry, widget_type: str) -> None:
        _check_widget_create(
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


class TestUserMessagesContent:
    def test_create(self, clients: ClientRegistry) -> None:
        _check_widget_create(clients, {"type": "user_messages"})


class TestSidebarElementContent:
    def test_create(self, clients: ClientRegistry) -> None:
        _check_widget_create(
            clients,
            {
                "type": "sidebar_element",
                "name": "sitestatus",
            },
        )

    def test_invalid_element_name(self, clients: ClientRegistry) -> None:
        resp = clients.DashboardClient.create_relative_grid_dashboard(
            _create_dashboard_payload(
                "test_dashboard",
                {
                    "test_widget": _create_widget(
                        {
                            "type": "sidebar_element",
                            "name": "non_existent_element",
                        }
                    )
                },
            ),
            expect_ok=False,
        )
        assert resp.status_code == 400, f"Expected 400, got {resp.status_code} {resp.body!r}"
        assert resp.json["fields"]["body.widgets.test_widget.content.sidebar_element.name"][
            "msg"
        ].startswith("Value error, Value 'non_existent_element' is not allowed, valid options are:")


class TestURLContent:
    def test_create(self, clients: ClientRegistry) -> None:
        _check_widget_create(
            clients,
            {
                "type": "url",
                "url": "https://example.com",
            },
        )


class TestStaticTextContent:
    def test_create(self, clients: ClientRegistry) -> None:
        _check_widget_create(
            clients,
            {
                "type": "static_text",
                "text": "This is a static text widget",
            },
        )

    def test_compute_widget_attributes(self, clients: ClientRegistry) -> None:
        resp = clients.DashboardClient.compute_widget_attributes(
            {
                "type": "static_text",
                "text": "This is a static text widget",
            }
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code} {resp.body!r}"
        assert set(resp.json["value"]) == {"filter_context"}
        assert resp.json["value"]["filter_context"]["uses_infos"] == []


class TestLinkedViewContent:
    def test_create(self, clients: ClientRegistry) -> None:
        _check_widget_create(
            clients,
            {
                "type": "linked_view",
                "view_name": "allhosts",
            },
        )

    def test_invalid_view_name(self, clients: ClientRegistry) -> None:
        resp = clients.DashboardClient.create_relative_grid_dashboard(
            _create_dashboard_payload(
                "test_dashboard",
                {
                    "test_widget": _create_widget(
                        {
                            "type": "linked_view",
                            "view_name": "non_existent_view",  # This view does not exist
                        }
                    )
                },
            ),
            expect_ok=False,
        )
        assert resp.status_code == 400, f"Expected 400, got {resp.status_code} {resp.body!r}"
        assert (
            resp.json["fields"]["body.widgets.test_widget.content.linked_view.view_name"]["msg"]
            == "Value error, View does not exist or you don't have permission to see it."
        )


class TestEmbeddedViewContent:
    @pytest.fixture(name="setup_embedded_view")
    def fixture_setup_embedded_view(
        self, clients: ClientRegistry, with_automation_user: tuple[UserId, str]
    ) -> tuple[str, str, str]:
        user_id = with_automation_user[0]
        dashboard_id = "test_dashboard"
        clients.DashboardClient.create_relative_grid_dashboard(
            _create_dashboard_payload(dashboard_id, {})
        )

        embedded_id = "some-random-id"
        embedded_view_datasource = "alert_stats"
        dashboards = get_all_dashboards()
        dashboards[(user_id, dashboard_id)]["embedded_views"] = {
            embedded_id: DashboardEmbeddedViewSpec(
                single_infos=[],
                datasource=embedded_view_datasource,
                layout="table",
                painters=[
                    ColumnSpec(name="alert_stats_problem"),
                    ColumnSpec(
                        name="host",
                        parameters={"color_choices": []},
                        link_spec=VisualLinkSpec(type_name="views", name="hostsvcevents"),
                    ),
                    ColumnSpec(
                        name="service_description",
                        link_spec=VisualLinkSpec(type_name="views", name="svcevents"),
                    ),
                ],
                group_painters=[],
                sorters=[
                    SorterSpec(sorter="alerts_crit", negate=False),
                    SorterSpec(sorter="alerts_unknown", negate=False),
                    SorterSpec(sorter="alerts_warn", negate=False),
                    SorterSpec(sorter="site_host", negate=True),
                    SorterSpec(sorter="svcdescr", negate=True),
                ],
                browser_reload=0,
                num_columns=1,
                column_headers="pergroup",
            )
        }
        return dashboard_id, embedded_id, embedded_view_datasource

    def test_edit(self, clients: ClientRegistry, setup_embedded_view: tuple[str, str, str]) -> None:
        # with the way embedded views work right now, there is no way to used them on create
        # so we have to use edit, and modify the underlying config first to set it up
        dashboard_id, embedded_id, embedded_view_datasource = setup_embedded_view

        payload = _create_dashboard_payload(
            dashboard_id,  # keep the same ID
            {
                "test_widget": _create_widget(
                    {
                        "type": "embedded_view",
                        "embedded_id": embedded_id,
                        "datasource": embedded_view_datasource,
                        "restricted_to_single": ["host"],
                    }
                ),
            },
        )
        resp = clients.DashboardClient.edit_relative_grid_dashboard(dashboard_id, payload)
        widgets = resp.json["extensions"]["widgets"]
        assert len(widgets) == 1, f"Expected 1 widget, got {len(widgets)}"
        widget = next(iter(widgets.values()))  # IDs are not consistent
        assert widget["content"]["type"] == "embedded_view"

    def test_mismatching_datasource(
        self, clients: ClientRegistry, setup_embedded_view: tuple[str, str, str]
    ) -> None:
        # with the way embedded views work right now, there is no way to used them on create
        # so we have to use edit, and modify the underlying config first to set it up
        dashboard_id, embedded_id, embedded_view_datasource = setup_embedded_view

        payload = _create_dashboard_payload(
            dashboard_id,
            {
                "test_widget": _create_widget(
                    {
                        "type": "embedded_view",
                        "embedded_id": embedded_id,
                        "datasource": "hosts",  # does not match the embedded view's datasource
                        "restricted_to_single": [],
                    }
                ),
            },
        )
        resp = clients.DashboardClient.edit_relative_grid_dashboard(
            dashboard_id, payload, expect_ok=False
        )
        assert resp.status_code == 400, f"Expected 400, got {resp.status_code} {resp.body!r}"
        assert (
            resp.json["fields"]["body.widgets.test_widget.content.embedded_view.datasource"]["msg"]
            == "Datasource does not match the embedded view definition."
        )

    def test_invalid_datasource(self, clients: ClientRegistry) -> None:
        payload = _create_dashboard_payload(
            "test_dashboard",
            {
                "test_widget": _create_widget(
                    {
                        "type": "embedded_view",
                        "embedded_id": "some-random-id",
                        "datasource": "non_existent_datasource",  # expected to not exist
                        "restricted_to_single": [],
                    }
                ),
            },
        )
        resp = clients.DashboardClient.create_relative_grid_dashboard(payload, expect_ok=False)
        assert resp.status_code == 400, f"Expected 400, got {resp.status_code} {resp.body!r}"
        assert resp.json["fields"]["body.widgets.test_widget.content.embedded_view.datasource"][
            "msg"
        ].startswith(
            "Value error, Value 'non_existent_datasource' is not allowed, valid options are:"
        )

    def test_invalid_info_names(self, clients: ClientRegistry) -> None:
        payload = _create_dashboard_payload(
            "test_dashboard",
            {
                "test_widget": _create_widget(
                    {
                        "type": "embedded_view",
                        "embedded_id": "some-random-id",
                        "datasource": "hosts",
                        "restricted_to_single": ["non_existent_info"],  # expected to not exist
                    }
                ),
            },
        )
        resp = clients.DashboardClient.create_relative_grid_dashboard(payload, expect_ok=False)
        assert resp.status_code == 400, f"Expected 400, got {resp.status_code} {resp.body!r}"
        assert resp.json["fields"][
            "body.widgets.test_widget.content.embedded_view.restricted_to_single.0"
        ]["msg"].startswith(
            "Value error, Value 'non_existent_info' is not allowed, valid options are:"
        )


@pytest.mark.usefixtures("skip_in_raw_edition")
@pytest.mark.parametrize("widget_type", ["ntop_alerts", "ntop_flows", "ntop_top_talkers"])
class TestNtopContent:
    def test_create(self, clients: ClientRegistry, widget_type: str) -> None:
        _check_widget_create(
            clients,
            {"type": widget_type},
        )


class TestNotSupportedContent:
    def test_create(self, clients: ClientRegistry) -> None:
        resp = clients.DashboardClient.create_relative_grid_dashboard(
            _create_dashboard_payload(
                "test_dashboard",
                {
                    "test_widget": _create_widget(
                        {"type": "not_supported", "original_type": "nodata"}
                    ),
                },
            ),
            expect_ok=False,
        )
        assert resp.status_code == 400, f"Expected 400, got {resp.status_code} {resp.body!r}"
        assert (
            resp.json["fields"]["body.widgets.test_widget.content.not_supported"]["msg"]
            == "Value error, Cannot use unsupported content type."
        )
