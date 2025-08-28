#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable, Mapping
from typing import Any, get_args, get_type_hints

import pytest

from cmk.gui.dashboard.api import ApiCustomGraphValidation
from cmk.gui.dashboard.api._model.widget_content import _CONTENT_TYPES
from cmk.gui.dashboard.api._model.widget_content._base import BaseWidgetContent
from cmk.gui.dashboard.api._utils import INTERNAL_TO_API_TYPE_NAME
from cmk.gui.views.icon.registry import all_icons
from cmk.utils.livestatus_helpers.testing import MockLiveStatusConnection
from tests.testlib.common.repo import (
    is_cloud_repo,
    is_enterprise_repo,
    is_managed_repo,
    is_saas_repo,
)
from tests.testlib.unit.rest_api_client import ClientRegistry


@pytest.mark.parametrize("widget_api_model", _CONTENT_TYPES)
def test_widget_api_model_has_valid_type_mapping(widget_api_model: BaseWidgetContent) -> None:
    literal_values = get_args(get_type_hints(widget_api_model)["type"])

    api_widget_type_name = literal_values[0] if literal_values else None
    internal_widget_type_name = widget_api_model.internal_type()
    mapped_api_type_name = INTERNAL_TO_API_TYPE_NAME.get(internal_widget_type_name)

    assert len(literal_values) == 1, "Widget content model  should have exactly one Literal value"

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


def test_list_dashboards(
    clients: ClientRegistry, mock_livestatus: MockLiveStatusConnection
) -> None:
    # NOTE: `mock_livestatus` is used, because graph widgets want the connected site PIDs.
    # No queries are actually executed.

    # we expect at least one builtin dashboard to be present, and that all of them can be serialized
    resp = clients.DashboardClient.get_all()
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code} {resp.body!r}"
    assert len(resp.json["value"]) > 0, "Expected at least one dashboard to be returned"


def test_show_dashboard(clients: ClientRegistry, mock_livestatus: MockLiveStatusConnection) -> None:
    # NOTE: `mock_livestatus` is used, because graph widgets want the connected site PIDs.
    # No queries are actually executed.

    # main builtin dashboard should always be present
    resp = clients.DashboardClient.get("main")
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code} {resp.body!r}"
    # check that we got the correct dashboard
    assert resp.json["id"] == "main", "Expected dashboard ID to be 'main'"


def test_show_non_existent_dashboard(clients: ClientRegistry) -> None:
    resp = clients.DashboardClient.get("non_existent" * 4, expect_ok=False)
    assert resp.status_code == 404, f"Expected 404, got {resp.status_code} {resp.body!r}"


def _create_dashboard_payload(
    dashboard_id: str,
    widgets: Mapping[str, Mapping[str, object]],
    icon_config: Mapping[str, object] | None = None,
) -> dict[str, object]:
    menu: dict[str, object] = {
        "topic": "general",
        "sort_index": 99,
        "search_terms": [],
        "is_show_more": False,
    }
    if icon_config is not None:
        menu["icon"] = icon_config
    return {
        "id": dashboard_id,
        "title": {"text": "Test Dashboard", "render": True, "include_context": False},
        "description": "This is a test dashboard",
        "menu": menu,
        "visibility": {
            "hide_in_monitor_menu": False,
            "hide_in_drop_down_menus": False,
            "share": "no",
        },
        "mandatory_context_filters": [],
        "filter_context": {"restricted_to_single": [], "filters": {}},
        "widgets": widgets,
    }


def _create_widget(content: dict[str, object]) -> dict[str, object]:
    return {
        "layout": {
            "relative_grid": {
                "position": {"x": 1, "y": 1},
                "size": {"width": 10, "height": 10},
            }
        },
        "general_settings": {
            "title": {"text": "Test Widget", "render_mode": "with_background"},
            "render_background": True,
        },
        "content": content,
        "filters": {},
    }


def test_create_empty_dashboard(clients: ClientRegistry) -> None:
    resp = clients.DashboardClient.create(_create_dashboard_payload("test_dashboard", {}))
    assert resp.status_code == 201, f"Expected 201, got {resp.status_code} {resp.body!r}"
    assert resp.json["id"] == "test_dashboard", (
        "Expected created dashboard ID to be 'test_dashboard'"
    )
    assert resp.json["extensions"]["widgets"] == {}, "Expected no widgets"


@pytest.mark.parametrize(
    "dashboard_id", [pytest.param("", id="empty"), "with whitespace", "with_special_chars!!!"]
)
def test_create_dashboard_with_invalid_id(clients: ClientRegistry, dashboard_id: str) -> None:
    resp = clients.DashboardClient.create(
        _create_dashboard_payload(dashboard_id, {}), expect_ok=False
    )
    assert resp.status_code == 400, f"Expected 400, got {resp.status_code} {resp.body!r}"
    assert resp.json["fields"]["body.id"]["msg"] == "String should match pattern '^[a-zA-Z0-9_]+$'"


def test_create_dashboard_with_invalid_widget_type(clients: ClientRegistry) -> None:
    payload = _create_dashboard_payload(
        "invalid_widget_type",
        {"test_widget": _create_widget({"type": "not_a_real_type"})},
    )
    resp = clients.DashboardClient.create(payload, expect_ok=False)
    assert resp.status_code == 400, f"Expected 400, got {resp.status_code} {resp.body!r}"


def test_delete_dashboard(clients: ClientRegistry) -> None:
    dashboard_id = "to_delete"
    clients.DashboardClient.create(_create_dashboard_payload(dashboard_id, {}))

    resp = clients.DashboardClient.delete(dashboard_id)
    assert resp.status_code == 204, f"Expected 204, got {resp.status_code} {resp.body!r}"
    resp = clients.DashboardClient.get(dashboard_id, expect_ok=False)
    assert resp.status_code == 404, f"Expected 404, got {resp.status_code} {resp.body!r}"


class TestDashboardIcon:
    def test_create_with_icon(self, clients: ClientRegistry) -> None:
        # use a random icon name, the list of available icons may change depending on editions
        icons = list(all_icons())
        icon_config = {"name": icons[0]}

        resp = clients.DashboardClient.create(
            _create_dashboard_payload("test_dashboard_with_icon", {}, icon_config=icon_config)
        )
        assert resp.status_code == 201, f"Expected 201, got {resp.status_code} {resp.body!r}"
        assert resp.json["extensions"]["menu"]["icon"] == icon_config, "Expected icon to be set"

    def test_create_with_icon_with_emblem(self, clients: ClientRegistry) -> None:
        # use a random icon name, the list of available icons may change depending on editions
        icons = list(all_icons())
        icon_config = {"name": icons[0], "emblem": icons[-1]}

        resp = clients.DashboardClient.create(
            _create_dashboard_payload("test_dashboard_with_icon", {}, icon_config=icon_config)
        )
        assert resp.status_code == 201, f"Expected 201, got {resp.status_code} {resp.body!r}"
        assert resp.json["extensions"]["menu"]["icon"] == icon_config, "Expected icon to be set"

    def test_invalid_icon_name(self, clients: ClientRegistry) -> None:
        resp = clients.DashboardClient.create(
            _create_dashboard_payload(
                "test_dashboard_with_invalid_icon",
                {},
                icon_config={"name": "non_existent_icon"},
            ),
            expect_ok=False,
        )
        assert resp.status_code == 400, f"Expected 400, got {resp.status_code} {resp.body!r}"
        assert resp.json["fields"]["body.menu.icon.DashboardIcon.name"]["msg"].startswith(
            "Value error, Value 'non_existent_icon' is not allowed, valid options are:"
        )


def _check_widget_create(
    clients: ClientRegistry,
    content: dict[str, object],
) -> None:
    expected_type = content["type"]
    resp = clients.DashboardClient.create(
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
    if is_saas_repo() or is_cloud_repo() or is_managed_repo() or is_enterprise_repo():
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

    @pytest.mark.parametrize(
        "graph_template",
        [
            "non_existent_graph",
            "METRIC_non_existent_metric",
        ],
    )
    def test_invalid_graph_template(self, clients: ClientRegistry, graph_template: str) -> None:
        resp = clients.DashboardClient.create(
            _create_dashboard_payload(
                "test_dashboard",
                {
                    "test_widget": _create_widget(
                        {
                            "type": "combined_graph",
                            "timerange": {"type": "predefined", "value": "last_25_hours"},
                            "graph_render_options": {},
                            "graph_template": graph_template,
                            "presentation": "lines",
                        }
                    )
                },
            ),
            expect_ok=False,
        )
        assert resp.status_code == 400, f"Expected 400, got {resp.status_code} {resp.body!r}"
        assert resp.json["fields"][
            "body.widgets.test_widget.content.combined_graph.graph_template"
        ]["msg"].startswith(
            f"Value error, Value '{graph_template.removeprefix('METRIC_')}' is not allowed, valid options are:"
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

    def test_invalid_metric(self, clients: ClientRegistry) -> None:
        resp = clients.DashboardClient.create(
            _create_dashboard_payload(
                "test_dashboard",
                {
                    "test_widget": _create_widget(
                        {
                            "type": "single_timeseries",
                            "timerange": {"type": "predefined", "value": "last_25_hours"},
                            "graph_render_options": {},
                            "metric": "non_existent_metric",
                            "color": "#ABCDEF",
                        }
                    )
                },
            ),
            expect_ok=False,
        )
        assert resp.status_code == 400, f"Expected 400, got {resp.status_code} {resp.body!r}"
        assert resp.json["fields"]["body.widgets.test_widget.content.single_timeseries.metric"][
            "msg"
        ].startswith("Value error, Value 'non_existent_metric' is not allowed, valid options are:")


@pytest.fixture(name="skip_custom_graph_validation")
def fixture_skip_custom_graph_validation() -> Iterable[None]:
    # we disable the validation, rather than creating a custom graph (which needs CEE stuff)
    old = ApiCustomGraphValidation.is_graph_valid
    try:
        ApiCustomGraphValidation.is_graph_valid = lambda _graph: True
        yield
    finally:
        ApiCustomGraphValidation.is_graph_valid = old


@pytest.mark.usefixtures("skip_in_raw_edition")
@pytest.mark.usefixtures("skip_custom_graph_validation")
class TestCustomGraphContent:
    def test_create(self, clients: ClientRegistry) -> None:
        _check_widget_create(
            clients,
            {
                "type": "custom_graph",
                "timerange": {"type": "predefined", "value": "last_25_hours"},
                "graph_render_options": {},
                "custom_graph": "???",  # the validation is disabled in the fixture
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

    def test_invalid_source(self, clients: ClientRegistry) -> None:
        resp = clients.DashboardClient.create(
            _create_dashboard_payload(
                "test_dashboard",
                {
                    "test_widget": _create_widget(
                        {
                            "type": "performance_graph",
                            "timerange": {"type": "predefined", "value": "last_25_hours"},
                            "graph_render_options": {},
                            "source": "non_existent_source",
                        }
                    )
                },
            ),
            expect_ok=False,
        )
        assert resp.status_code == 400, f"Expected 400, got {resp.status_code} {resp.body!r}"
        assert resp.json["fields"][
            "body.widgets.test_widget.content.performance_graph.source.function-after[validate(), str]"
        ]["msg"].startswith(
            "Value error, Value 'non_existent_source' is not allowed, valid options are:"
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

    def test_invalid_metric(self, clients: ClientRegistry) -> None:
        resp = clients.DashboardClient.create(
            _create_dashboard_payload(
                "test_dashboard",
                {
                    "test_widget": _create_widget(
                        {
                            "type": "barplot",
                            "metric": "non_existent_metric",
                            "display_range": "automatic",
                        }
                    )
                },
            ),
            expect_ok=False,
        )
        assert resp.status_code == 400, f"Expected 400, got {resp.status_code} {resp.body!r}"
        assert resp.json["fields"]["body.widgets.test_widget.content.barplot.metric"][
            "msg"
        ].startswith("Value error, Value 'non_existent_metric' is not allowed, valid options are:")

    def test_invalid_display_range_unit(self, clients: ClientRegistry) -> None:
        resp = clients.DashboardClient.create(
            _create_dashboard_payload(
                "test_dashboard",
                {
                    "test_widget": _create_widget(
                        {
                            "type": "barplot",
                            "metric": "availability",
                            "display_range": {
                                "type": "fixed",
                                "unit": "invalid",
                                "minimum": 0,
                                "maximum": 100,
                            },
                        }
                    )
                },
            ),
            expect_ok=False,
        )
        assert resp.status_code == 400, f"Expected 400, got {resp.status_code} {resp.body!r}"
        assert resp.json["fields"]["body.widgets.test_widget.content.barplot"]["msg"].startswith(
            "Value error, Unit of the display range 'invalid' does not match the unit of the metric: %"
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

    def test_invalid_metric(self, clients: ClientRegistry) -> None:
        resp = clients.DashboardClient.create(
            _create_dashboard_payload(
                "test_dashboard",
                {
                    "test_widget": _create_widget(
                        {
                            "type": "gauge",
                            "metric": "non_existent_metric",
                            "display_range": "automatic",
                            "time_range": "current",
                            "status_display": {
                                "type": "text",
                                "for_states": "not_ok",
                            },
                        }
                    )
                },
            ),
            expect_ok=False,
        )
        assert resp.status_code == 400, f"Expected 400, got {resp.status_code} {resp.body!r}"
        assert resp.json["fields"]["body.widgets.test_widget.content.gauge.metric"][
            "msg"
        ].startswith("Value error, Value 'non_existent_metric' is not allowed, valid options are:")

    def test_invalid_display_range_unit(self, clients: ClientRegistry) -> None:
        resp = clients.DashboardClient.create(
            _create_dashboard_payload(
                "test_dashboard",
                {
                    "test_widget": _create_widget(
                        {
                            "type": "gauge",
                            "metric": "availability",
                            "display_range": {
                                "type": "fixed",
                                "unit": "invalid",
                                "minimum": 0,
                                "maximum": 100,
                            },
                            "time_range": "current",
                            "status_display": {"type": "text", "for_states": "not_ok"},
                        }
                    )
                },
            ),
            expect_ok=False,
        )
        assert resp.status_code == 400, f"Expected 400, got {resp.status_code} {resp.body!r}"
        assert resp.json["fields"]["body.widgets.test_widget.content.gauge"]["msg"].startswith(
            "Value error, Unit of the display range 'invalid' does not match the unit of the metric: %"
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

    def test_invalid_metric(self, clients: ClientRegistry) -> None:
        resp = clients.DashboardClient.create(
            _create_dashboard_payload(
                "test_dashboard",
                {
                    "test_widget": _create_widget(
                        {
                            "type": "single_metric",
                            "metric": "non_existent_metric",
                            "time_range": "current",
                            "status_display": {"type": "text", "for_states": "not_ok"},
                            "display_range": "automatic",
                            "show_display_range_limits": False,
                        }
                    )
                },
            ),
            expect_ok=False,
        )
        assert resp.status_code == 400, f"Expected 400, got {resp.status_code} {resp.body!r}"
        assert resp.json["fields"]["body.widgets.test_widget.content.single_metric.metric"][
            "msg"
        ].startswith("Value error, Value 'non_existent_metric' is not allowed, valid options are:")

    def test_invalid_display_range_unit(self, clients: ClientRegistry) -> None:
        resp = clients.DashboardClient.create(
            _create_dashboard_payload(
                "test_dashboard",
                {
                    "test_widget": _create_widget(
                        {
                            "type": "single_metric",
                            "metric": "availability",
                            "time_range": "current",
                            "status_display": {"type": "text", "for_states": "not_ok"},
                            "display_range": {
                                "type": "fixed",
                                "unit": "invalid",
                                "minimum": 0,
                                "maximum": 100,
                            },
                            "show_display_range_limits": False,
                        }
                    )
                },
            ),
            expect_ok=False,
        )
        assert resp.status_code == 400, f"Expected 400, got {resp.status_code} {resp.body!r}"
        assert resp.json["fields"]["body.widgets.test_widget.content.single_metric"][
            "msg"
        ].startswith(
            "Value error, Unit of the display range 'invalid' does not match the unit of the metric: %"
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

    def test_invalid_metric(self, clients: ClientRegistry) -> None:
        resp = clients.DashboardClient.create(
            _create_dashboard_payload(
                "test_dashboard",
                {
                    "test_widget": _create_widget(
                        {
                            "type": "average_scatterplot",
                            "timerange": {"type": "predefined", "value": "last_25_hours"},
                            "metric": "non_existent_metric",
                            "metric_color": "default",
                            "average_color": "default",
                            "median_color": "default",
                        }
                    )
                },
            ),
            expect_ok=False,
        )
        assert resp.status_code == 400, f"Expected 400, got {resp.status_code} {resp.body!r}"
        assert resp.json["fields"]["body.widgets.test_widget.content.average_scatterplot.metric"][
            "msg"
        ].startswith("Value error, Value 'non_existent_metric' is not allowed, valid options are:")


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

    def test_invalid_metric(self, clients: ClientRegistry) -> None:
        resp = clients.DashboardClient.create(
            _create_dashboard_payload(
                "test_dashboard",
                {
                    "test_widget": _create_widget(
                        {
                            "type": "top_list",
                            "metric": "non_existent_metric",
                            "display_range": "automatic",
                            "columns": {
                                "show_service_description": False,
                                "show_bar_visualization": False,
                            },
                            "ranking_order": "low",
                            "limit_to": 10,
                        }
                    )
                },
            ),
            expect_ok=False,
        )
        assert resp.status_code == 400, f"Expected 400, got {resp.status_code} {resp.body!r}"
        assert resp.json["fields"]["body.widgets.test_widget.content.top_list.metric"][
            "msg"
        ].startswith("Value error, Value 'non_existent_metric' is not allowed, valid options are:")

    def test_invalid_display_range_unit(self, clients: ClientRegistry) -> None:
        resp = clients.DashboardClient.create(
            _create_dashboard_payload(
                "test_dashboard",
                {
                    "test_widget": _create_widget(
                        {
                            "type": "top_list",
                            "metric": "availability",
                            "display_range": {
                                "type": "fixed",
                                "unit": "invalid",
                                "minimum": 0,
                                "maximum": 100,
                            },
                            "columns": {
                                "show_service_description": False,
                                "show_bar_visualization": False,
                            },
                            "ranking_order": "low",
                            "limit_to": 10,
                        }
                    )
                },
            ),
            expect_ok=False,
        )
        assert resp.status_code == 400, f"Expected 400, got {resp.status_code} {resp.body!r}"
        assert resp.json["fields"]["body.widgets.test_widget.content.top_list"]["msg"].startswith(
            "Value error, Unit of the display range 'invalid' does not match the unit of the metric: %"
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
        resp = clients.DashboardClient.create(
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
        resp = clients.DashboardClient.create(
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
    @staticmethod
    def _create_embedded_view_content() -> dict[str, Any]:
        return {
            "type": "embedded_view",
            "restricted_to_single": [],
            "datasource": "alert_stats",
            "layout": "table",
            "columns": [
                {"name": "alert_stats_problem", "parameters": {}, "type": "column"},
                {
                    "name": "host",
                    "parameters": {"color_choices": []},
                    "link_spec": {"type": "views", "name": "hostsvcevents"},
                    "type": "column",
                },
                {
                    "name": "service_description",
                    "parameters": {},
                    "link_spec": {"type": "views", "name": "svcevents"},
                    "type": "column",
                },
            ],
            "sorters": [
                {"sorter_name": "alerts_crit", "parameters": {}, "direction": "desc"},
                {"sorter_name": "alerts_unknown", "parameters": {}, "direction": "desc"},
                {"sorter_name": "alerts_warn", "parameters": {}, "direction": "desc"},
                {"sorter_name": "site_host", "parameters": {}, "direction": "asc"},
                {"sorter_name": "svcdescr", "parameters": {}, "direction": "asc"},
            ],
            "reload_interval_seconds": 0,
            "entries_per_row": 1,
            "column_headers": "pergroup",
        }

    def test_create(self, clients: ClientRegistry) -> None:
        _check_widget_create(clients, self._create_embedded_view_content())

    def test_invalid_restricted_to_single(self, clients: ClientRegistry) -> None:
        content = self._create_embedded_view_content()
        content["restricted_to_single"] = ["invalid_info_name"]
        resp = clients.DashboardClient.create(
            _create_dashboard_payload(
                "test_dashboard",
                {"test_widget": _create_widget(content)},
            ),
            expect_ok=False,
        )
        assert resp.status_code == 400, f"Expected 400, got {resp.status_code} {resp.body!r}"
        assert resp.json["fields"][
            "body.widgets.test_widget.content.embedded_view.restricted_to_single.0"
        ]["msg"].startswith(
            "Value error, Value 'invalid_info_name' is not allowed, valid options are:"
        )
        assert len(resp.json["fields"]) == 1, "Expected only one field error"

    def test_invalid_data_source(self, clients: ClientRegistry) -> None:
        content = self._create_embedded_view_content()
        content["datasource"] = "non_existent_datasource"
        resp = clients.DashboardClient.create(
            _create_dashboard_payload(
                "test_dashboard",
                {"test_widget": _create_widget(content)},
            ),
            expect_ok=False,
        )
        assert resp.status_code == 400, f"Expected 400, got {resp.status_code} {resp.body!r}"
        assert resp.json["fields"]["body.widgets.test_widget.content.embedded_view.datasource"][
            "msg"
        ].startswith(
            "Value error, Value 'non_existent_datasource' is not allowed, valid options are:"
        )
        assert len(resp.json["fields"]) == 1, "Expected only one field error"

    def test_invalid_layout(self, clients: ClientRegistry) -> None:
        content = self._create_embedded_view_content()
        content["layout"] = "non_existent_layout"
        resp = clients.DashboardClient.create(
            _create_dashboard_payload(
                "test_dashboard",
                {"test_widget": _create_widget(content)},
            ),
            expect_ok=False,
        )
        assert resp.status_code == 400, f"Expected 400, got {resp.status_code} {resp.body!r}"
        assert resp.json["fields"]["body.widgets.test_widget.content.embedded_view.layout"][
            "msg"
        ].startswith("Value error, Value 'non_existent_layout' is not allowed, valid options are:")
        assert len(resp.json["fields"]) == 1, "Expected only one field error"

    def test_invalid_painter_name(self, clients: ClientRegistry) -> None:
        content = self._create_embedded_view_content()
        content["columns"][0]["name"] = "non_existent_painter"
        resp = clients.DashboardClient.create(
            _create_dashboard_payload(
                "test_dashboard",
                {"test_widget": _create_widget(content)},
            ),
            expect_ok=False,
        )
        assert resp.status_code == 400, f"Expected 400, got {resp.status_code} {resp.body!r}"
        assert resp.json["fields"][
            "body.widgets.test_widget.content.embedded_view.columns.0.column.name"
        ]["msg"].startswith("Painter 'non_existent_painter' does not exist.")
        assert len(resp.json["fields"]) == 1, "Expected only one field error"

    def test_invalid_link_spec(self, clients: ClientRegistry) -> None:
        content = self._create_embedded_view_content()
        content["columns"][1]["link_spec"]["name"] = "non_existent_view"
        resp = clients.DashboardClient.create(
            _create_dashboard_payload(
                "test_dashboard",
                {"test_widget": _create_widget(content)},
            ),
            expect_ok=False,
        )
        assert resp.status_code == 400, f"Expected 400, got {resp.status_code} {resp.body!r}"
        assert resp.json["fields"][
            "body.widgets.test_widget.content.embedded_view.columns.1.column.link_spec.function-after[_validate(), ApiVisualLink]"
        ]["msg"].startswith(
            "Value error, View 'non_existent_view' does not exist or you don't have permission to see it."
        )
        # link_spec can be omitted, so there are two validation errors here (we don't yet filter out ApiOmitted errors)
        assert len(resp.json["fields"]) == 2, "Expected two field errors"
        assert all(
            error.startswith(
                "body.widgets.test_widget.content.embedded_view.columns.1.column.link_spec"
            )
            for error in resp.json["fields"]
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
        resp = clients.DashboardClient.create(
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
