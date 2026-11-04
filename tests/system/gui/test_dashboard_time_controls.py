#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""The time controls of a dashboard.

E2E rather than Vitest: a widget draws the range from the data the backend fetches for it,
and a widget showing a view renders it as a server-side page in an iframe.
"""

import re
import time
from collections.abc import Callable, Generator, Iterator, Mapping, Sequence
from contextlib import contextmanager
from datetime import datetime
from typing import Final, NamedTuple

import pytest
from playwright.sync_api import expect, Page, Request

from tests.system.gui.testlib.playwright.pom.graphing.dashboard_graph_widget import (
    DashboardGraphWidget,
)
from tests.system.gui.testlib.playwright.pom.graphing.fixtures import SERVICE_WITH_GRAPHS
from tests.system.gui.testlib.playwright.pom.graphing.global_time_picker import (
    GlobalTimePicker,
    PickerMoment,
)
from tests.system.gui.testlib.playwright.pom.graphing.graph_accessor import GraphAccessor
from tests.system.gui.testlib.playwright.pom.graphing.graph_surfaces import GraphContainment
from tests.system.gui.testlib.playwright.pom.graphing.timeseries_graph import GraphPanel
from tests.system.gui.testlib.playwright.pom.monitor.custom_dashboard import CustomDashboard
from tests.system.gui.testlib.playwright.pom.monitor.dashboard import BaseDashboard, MainDashboard
from tests.system.gui.testlib.playwright.pom.sidebar.widget_wizard_sidebar import (
    MetricsAndGraphsWidgetWizard,
    ServiceMetricDropdownOptions,
    VisualizationType,
)
from tests.testlib.common.utils import wait_until
from tests.testlib.common.utils2 import is_cleanup_enabled
from tests.testlib.system.site import ADMIN_USER, Site

_INHERITING_DASHBOARD_ID: Final = "e2e_inheriting_time_range_dashboard"
_INHERITING_DASHBOARD_TITLE: Final = "E2E inheriting time range dashboard"
_INHERITING_WIDGET_TITLES: Final = ("Inheriting graph A", "Inheriting graph B")

_MIXED_DASHBOARD_ID: Final = "e2e_mixed_time_range_dashboard"
_MIXED_DASHBOARD_TITLE: Final = "E2E mixed time range dashboard"
_INHERITING_WIDGET_TITLE: Final = "Inheriting graph"
_OVERRIDING_WIDGET_TITLE: Final = "Overriding graph"

_ZOOM_DASHBOARD_ID: Final = "e2e_zoom_time_range_dashboard"
_ZOOM_DASHBOARD_TITLE: Final = "E2E zoom time range dashboard"

_VIEW_DASHBOARD_ID: Final = "e2e_view_time_range_dashboard"
_VIEW_DASHBOARD_TITLE: Final = "E2E view time range dashboard"
_VIEW_WIDGET_TITLE: Final = "Graphs view"
# A classic view whose content depends on the time range: its rows are server-rendered and do
# not take the range, but the engine graphs its painter mounts do.
_GRAPHS_VIEW: Final = "service_graphs"

_REFRESH_DASHBOARD_ID: Final = "e2e_refresh_tick_dashboard"
_REFRESH_DASHBOARD_TITLE: Final = "E2E refresh tick dashboard"
_REFRESH_GRAPH_TITLE: Final = "Refreshing graph"
_REFRESH_FIGURE_TITLE: Final = "Refreshing figure"
_REFRESH_VIEW_TITLE: Final = "Refreshing view"
# A plain classic view: server-rendered rows and no engine graph, whose own data requests
# would be told apart from the graph widget's only by their frame.
_PLAIN_VIEW: Final = "allhosts"
# The dashboard's refresh interval when the user set no preference.
_REFRESH_INTERVAL_SECONDS: Final = 30
# Time for a widget to answer a tick on a slow site: the view's reload goes through a message
# to its iframe first.
_TICK_ANSWER_SECONDS: Final = 15
_POLL_MS: Final = 500
# A graph fetches on its own storage grid, so its window may end up to a step past the one
# requested; a step is a few minutes at most for a window of hours.
_FETCH_ALIGNMENT_SECONDS: Final = 600
# How long before the next tick the count is closed, so that tick cannot reach it.
_NEXT_TICK_MARGIN_SECONDS: Final = 5

_WIDGET_SIZE: Final = {"width": 40, "height": 20}
_FOLLOW_DASHBOARD: Final = "dashboard"
_OWN_FOUR_HOURS: Final = {"type": "graph", "duration": 4 * 60 * 60}

OTHER_PRESET: Final = "Last 25 h"
# What the condensed picker's dropdown reads once the window matches no preset.
_CUSTOM_RANGE: Final = "Custom range"

# Only a window wider than a day spans two dates, so a shifted hour cannot match.
_TWO_DATE_WINDOW: Final = re.compile(r"\d{4}-\d{2}-\d{2} — \d{4}-\d{2}-\d{2}")


def _whole_graph_of_one_service(wizard: MetricsAndGraphsWidgetWizard, host_name: str) -> None:
    wizard.select_single_host(host_name)
    wizard.select_single_service(SERVICE_WITH_GRAPHS)
    wizard.combined_graph_toggle.click()
    wizard.open_service_graph_dropdown().first.click()
    wizard.next_step_visualization_button.click()


def _whole_graph_of_matching_services(wizard: MetricsAndGraphsWidgetWizard, host_name: str) -> None:
    wizard.select_multiple_hosts_by_regex(f"^{re.escape(host_name)}$")
    wizard.select_multiple_services_by_regex(f"^{re.escape(SERVICE_WITH_GRAPHS)}$")
    wizard.combined_graph_toggle.click()
    wizard.open_service_graph_dropdown().first.click()
    wizard.next_step_visualization_button.click()


def _one_metric_of_one_service(
    visualization: VisualizationType,
) -> Callable[[MetricsAndGraphsWidgetWizard, str], None]:
    def select(wizard: MetricsAndGraphsWidgetWizard, host_name: str) -> None:
        wizard.select_single_host(host_name)
        wizard.select_single_service(_METRIC_SERVICE)
        wizard.single_metric_toggle.click()
        wizard.select_service_metric(_METRIC)
        wizard.select_visualization_type(visualization)

    return select


def _one_metric_of_matching_services(wizard: MetricsAndGraphsWidgetWizard, host_name: str) -> None:
    wizard.select_multiple_hosts_by_regex(f"^{re.escape(host_name)}$")
    wizard.select_multiple_services_by_regex(f"^{re.escape(_METRIC_SERVICE)}$")
    wizard.single_metric_toggle.click()
    wizard.select_service_metric(_METRIC)
    wizard.select_visualization_type(VisualizationType.SCATTERPLOT)


class _TimeRangeWidget(NamedTuple):
    """A 'Metrics & graphs' widget type with a time range setting, by how its wizard gets there.

    `select_data` picks the data on the first stage and moves on to the visualization stage.
    """

    select_data: Callable[[MetricsAndGraphsWidgetWizard, str], None]


# A metric every agent host reports, on the service every agent host carries.
_METRIC_SERVICE: Final = "Check_MK"
_METRIC: Final = ServiceMetricDropdownOptions.TOTAL_EXECUTION_TIME

# The 'Metrics & graphs' widgets with a time range setting: gauge, barplot and top list have
# none. The community edition restricts the wizard to one host, one service and a whole graph
# of it, which it draws as a performance graph; every other widget type needs a non-free one.
_TIME_RANGE_WIDGETS: Final = [
    pytest.param(_TimeRangeWidget(_whole_graph_of_one_service), id="performance_graph"),
    *(
        pytest.param(widget, id=widget_id, marks=pytest.mark.skip_if_edition("community"))
        for widget_id, widget in (
            ("combined_graph", _TimeRangeWidget(_whole_graph_of_matching_services)),
            (
                "single_timeseries",
                _TimeRangeWidget(_one_metric_of_one_service(VisualizationType.GRAPH)),
            ),
            (
                "single_metric",
                _TimeRangeWidget(_one_metric_of_one_service(VisualizationType.METRIC)),
            ),
            ("scatterplot", _TimeRangeWidget(_one_metric_of_matching_services)),
        )
    ),
]

# What a graph widget's own range selector offers with the site's default graph time ranges:
# those ranges, the calendar ones, then the two custom entries.
_GRAPH_WIDGET_RANGES: Final = [
    "Last 1 h",
    "Last 4 h",
    "Last 25 h",
    "Last 8 d",
    "Last 35 d",
    "Last 400 d",
    "Today",
    "Yesterday",
    "7 days back (this day last week)",
    "8 days back",
    "This week",
    "Last week",
    "2 weeks back",
    "This month",
    "Last month",
    "This year",
    "Last year",
    "The last...",
    "Date range",
]
_OVERRIDE_RANGE: Final = "Last 4 h"
# The option graph widgets offered before following the dashboard was possible.
_LEGACY_FIXED_TIMERANGE: Final = "Do not follow timerange changes"


class _FigureWidget(NamedTuple):
    """A figure widget: its content and the compute endpoint that answers it."""

    content: Mapping[str, object]
    compute_endpoint: str
    # Whether it draws one service's metric, and so takes the host and service filters.
    of_one_service: bool


# The single metric figure needs a non-free edition. The host statistics figure refreshes
# through the same path in every edition, so the community edition is covered too.
_REFRESHING_FIGURES: Final = [
    pytest.param(
        _FigureWidget(
            {"type": "host_stats", "contextual_link": {"type": "default"}},
            "/domain-types/dashboard/actions/compute-stats/invoke",
            of_one_service=False,
        ),
        id="host_stats",
    ),
    pytest.param(
        _FigureWidget(
            {
                "type": "single_metric",
                "metric": "mem_used",
                "time_range": {
                    "type": "window",
                    "window": "dashboard",
                    "consolidation": "average",
                },
                "status_display": {"type": "text", "for_states": "not_ok"},
                "display_range": "automatic",
                "show_display_range_limits": False,
                "show_delta": False,
            },
            "/domain-types/dashboard/actions/compute-single-metric/invoke",
            of_one_service=True,
        ),
        id="single_metric",
        marks=pytest.mark.skip_if_edition("community"),
    ),
]


# A moment some time back, in the browser's time zone and to the minute, as the picker's
# fields take it, with its epoch seconds.
_BROWSER_MOMENT_AGO: Final = """(secondsAgo) => {
    const moment = new Date(Date.now() - secondsAgo * 1000);
    moment.setSeconds(0, 0);
    return [moment.getTime() / 1000, moment.getFullYear(), moment.getMonth() + 1,
            moment.getDate(), moment.getHours(), moment.getMinutes()];
}"""


def _browser_moment_ago(page: Page, seconds: int) -> tuple[float, PickerMoment]:
    epoch, *fields = page.evaluate(_BROWSER_MOMENT_AGO, seconds)
    return epoch, PickerMoment(*fields)


def _requested_window_end(request: Request, window_field: str) -> object:
    """Where the time window a data request carries in its `window_field` ends."""
    body = request.post_data_json
    window = body.get(window_field) if isinstance(body, dict) else None
    assert isinstance(window, dict), f"{request.url} carried no {window_field!r}: {body!r}"
    return window["end"]


def _mark_document(dashboard: BaseDashboard) -> None:
    """Tag the document so a full page reload is detectable by the tag's absence."""
    dashboard.page.evaluate("window.__cmkDashboardTimeControlsMarker = true")


def _document_survived(dashboard: BaseDashboard) -> bool:
    return bool(dashboard.page.evaluate("window.__cmkDashboardTimeControlsMarker === true"))


# Collects every message the iframe's document receives, so the test can tell how the
# dashboard handed it the range.
_RECORD_MESSAGES: Final = """() => {
    window.__cmkReceivedMessages = [];
    window.addEventListener("message", (event) => window.__cmkReceivedMessages.push(event.data));
}"""
# The longest window among the time range messages received so far, in seconds.
_LONGEST_POSTED_RANGE: Final = """() => Math.max(0, ...window.__cmkReceivedMessages
    .filter((data) => data?.type === "cmk:dashboard:time-range")
    .map((data) => (Date.parse(data.range.end) - Date.parse(data.range.start)) / 1000))"""
_OTHER_PRESET_SECONDS: Final = 25 * 60 * 60


def _host_service_filters(host_name: str) -> dict[str, object]:
    return {"host": {"host": host_name}, "service": {"service": SERVICE_WITH_GRAPHS}}


def _widget(
    title: str, content: Mapping[str, object], filters: Mapping[str, object], y: int
) -> dict[str, object]:
    """One widget of a relative-grid dashboard, stacked in a single column at row `y`."""
    return {
        "general_settings": {
            "title": {"text": title, "render_mode": "with_background"},
            "render_background": True,
        },
        "content": dict(content),
        "filters": dict(filters),
        "layout": {
            "type": "relative_grid",
            "position": {"x": 1, "y": y},
            "size": _WIDGET_SIZE,
        },
    }


def _template_graph_ids(test_site: Site, host_name: str) -> list[str]:
    """The ids of the template graphs the host's service draws."""
    discovered = test_site.openapi.graph.discover_template_graphs(host_name, SERVICE_WITH_GRAPHS)
    graph_ids = [
        graph["add_to_specification"]["graph_id"]
        for graph in discovered["graphs"]
        if graph["add_to_specification"] is not None
    ]
    assert graph_ids, (
        f"{host_name}/{SERVICE_WITH_GRAPHS} yielded no template graph: "
        f"{discovered['no_data_message']}"
    )
    return graph_ids


def _template_graph_content(graph_id: str, timerange: object) -> dict[str, object]:
    """A template graph widget drawing the given time range.

    It shows the graph time, which states the window the widget last drew.
    """
    return {
        "type": "performance_graph",
        "timerange": timerange,
        "graph_render_options": {"show_graph_time": True},
        "source": graph_id,
    }


@contextmanager
def _open_dashboard(
    dashboard_page: MainDashboard,
    test_site: Site,
    *,
    dashboard_id: str,
    title: str,
    widgets: Mapping[str, Mapping[str, object]],
) -> Generator[CustomDashboard]:
    """A dashboard of the given widgets, opened in the browser.

    Built through the REST API: the wizard is not what is under test here. Shared with all
    users, because on the cloud edition the browser does not log in as `ADMIN_USER`.
    """
    payload = {
        "id": dashboard_id,
        "general_settings": {
            "title": {"text": title, "render": True, "include_context": False},
            "description": "",
            "menu": {
                "topic": "overview",
                "sort_index": 99,
                "search_terms": [],
                "is_show_more": False,
            },
            "visibility": {
                "hide_in_monitor_menu": False,
                "hide_in_drop_down_menus": False,
                "share": {"type": "with_all_users"},
            },
        },
        "filter_context": {
            "restricted_to_single": [],
            "filters": {},
            "mandatory_context_filters": [],
        },
        "widgets": dict(widgets),
        "layout": {"type": "relative_grid"},
    }
    with test_site.openapi.acting_as(ADMIN_USER, test_site.admin_password):
        test_site.openapi.dashboard.create_relative_grid_dashboard(payload)
    try:
        dashboard_page.page.goto(
            test_site.internal_url + f"dashboard.py?name={dashboard_id}&owner={ADMIN_USER}",
            wait_until="load",
        )
        yield CustomDashboard(dashboard_page.page, page_title=title, navigate_to_page=False)
    finally:
        if is_cleanup_enabled():
            with test_site.openapi.acting_as(ADMIN_USER, test_site.admin_password):
                test_site.openapi.dashboard.delete(dashboard_id)


@contextmanager
def _open_graph_dashboard(
    dashboard_page: MainDashboard,
    test_site: Site,
    host_name: str,
    *,
    dashboard_id: str,
    title: str,
    widgets: Sequence[tuple[str, object]],
) -> Generator[CustomDashboard]:
    """A dashboard of template graph widgets, given by title and time range, opened in the
    browser.

    The widgets take the service's graphs in turn, starting over if there are more widgets
    than graphs.
    """
    graph_ids = _template_graph_ids(test_site, host_name)
    with _open_dashboard(
        dashboard_page,
        test_site,
        dashboard_id=dashboard_id,
        title=title,
        widgets={
            f"graph_{index}": _widget(
                widget_title,
                _template_graph_content(graph_ids[index % len(graph_ids)], timerange),
                _host_service_filters(host_name),
                y=1 + 20 * index,
            )
            for index, (widget_title, timerange) in enumerate(widgets)
        },
    ) as dashboard:
        yield dashboard


@pytest.fixture(name="inheriting_dashboard")
def fixture_inheriting_dashboard(
    dashboard_page: MainDashboard,
    test_site: Site,
    graph_hosts_with_varying_data: list[str],
    javascript_errors: list[str],  # noqa: ARG001
) -> Iterator[CustomDashboard]:
    """A dashboard of two graph widgets that follow its time range, opened in the browser.

    Depends on `javascript_errors` so its listener is attached before this navigates.
    """
    with _open_graph_dashboard(
        dashboard_page,
        test_site,
        graph_hosts_with_varying_data[0],
        dashboard_id=_INHERITING_DASHBOARD_ID,
        title=_INHERITING_DASHBOARD_TITLE,
        widgets=[(title, _FOLLOW_DASHBOARD) for title in _INHERITING_WIDGET_TITLES],
    ) as dashboard:
        yield dashboard


@pytest.fixture(name="mixed_time_range_dashboard")
def fixture_mixed_time_range_dashboard(
    dashboard_page: MainDashboard,
    test_site: Site,
    graph_hosts_with_varying_data: list[str],
    javascript_errors: list[str],  # noqa: ARG001
) -> Iterator[CustomDashboard]:
    """A dashboard of one graph widget following its time range and one keeping its own four
    hours, opened in the browser.

    Depends on `javascript_errors` so its listener is attached before this navigates.
    """
    with _open_graph_dashboard(
        dashboard_page,
        test_site,
        graph_hosts_with_varying_data[0],
        dashboard_id=_MIXED_DASHBOARD_ID,
        title=_MIXED_DASHBOARD_TITLE,
        widgets=[
            (_INHERITING_WIDGET_TITLE, _FOLLOW_DASHBOARD),
            (_OVERRIDING_WIDGET_TITLE, _OWN_FOUR_HOURS),
        ],
    ) as dashboard:
        yield dashboard


@pytest.fixture(name="zoom_dashboard")
def fixture_zoom_dashboard(
    dashboard_page: MainDashboard,
    test_site: Site,
    graph_hosts_with_varying_data: list[str],
    javascript_errors: list[str],  # noqa: ARG001
) -> Iterator[CustomDashboard]:
    """A dashboard of two graph widgets following its time range and one keeping its own four
    hours, opened in the browser.

    Depends on `javascript_errors` so its listener is attached before this navigates.
    """
    with _open_graph_dashboard(
        dashboard_page,
        test_site,
        graph_hosts_with_varying_data[0],
        dashboard_id=_ZOOM_DASHBOARD_ID,
        title=_ZOOM_DASHBOARD_TITLE,
        widgets=[
            *((title, _FOLLOW_DASHBOARD) for title in _INHERITING_WIDGET_TITLES),
            (_OVERRIDING_WIDGET_TITLE, _OWN_FOUR_HOURS),
        ],
    ) as dashboard:
        yield dashboard


@pytest.fixture(name="view_dashboard")
def fixture_view_dashboard(
    dashboard_page: MainDashboard,
    test_site: Site,
    graph_hosts_with_varying_data: list[str],
    javascript_errors: list[str],  # noqa: ARG001
) -> Iterator[CustomDashboard]:
    """A dashboard of one classic view widget showing a service's graphs, opened in the
    browser.

    Depends on `javascript_errors` so its listener is attached before this navigates.
    """
    with _open_dashboard(
        dashboard_page,
        test_site,
        dashboard_id=_VIEW_DASHBOARD_ID,
        title=_VIEW_DASHBOARD_TITLE,
        widgets={
            "view": _widget(
                _VIEW_WIDGET_TITLE,
                {"type": "linked_view", "view_name": _GRAPHS_VIEW},
                _host_service_filters(graph_hosts_with_varying_data[0]),
                y=1,
            )
        },
    ) as dashboard:
        yield dashboard


def _open_new_widget_time_settings(
    dashboard: CustomDashboard, host_name: str, widget: _TimeRangeWidget
) -> MetricsAndGraphsWidgetWizard:
    """Start adding a widget of the host's data and go on to its time settings."""
    dashboard.enter_edit_widgets_mode()
    wizard = dashboard.open_add_widget_sidebar(MetricsAndGraphsWidgetWizard)
    widget.select_data(wizard, host_name)
    expect(
        wizard.time_range_settings.follow_dashboard_radio,
        "The visualization stage offers no time range setting",
    ).to_be_visible()
    return wizard


@pytest.fixture(name="refresh_dashboard")
def fixture_refresh_dashboard(
    figure: _FigureWidget,
    dashboard_page: MainDashboard,
    test_site: Site,
    graph_hosts_with_varying_data: list[str],
    javascript_errors: list[str],  # noqa: ARG001
) -> Iterator[CustomDashboard]:
    """A dashboard of one widget per refresh path - a graph, a figure and a classic view -
    opened in the browser.

    Depends on `javascript_errors` so its listener is attached before this navigates.
    """
    host_name = graph_hosts_with_varying_data[0]
    filters = _host_service_filters(host_name)
    with _open_dashboard(
        dashboard_page,
        test_site,
        dashboard_id=_REFRESH_DASHBOARD_ID,
        title=_REFRESH_DASHBOARD_TITLE,
        widgets={
            "graph": _widget(
                _REFRESH_GRAPH_TITLE,
                _template_graph_content(
                    _template_graph_ids(test_site, host_name)[0], _FOLLOW_DASHBOARD
                ),
                filters,
                y=1,
            ),
            "figure": _widget(
                _REFRESH_FIGURE_TITLE,
                figure.content,
                filters if figure.of_one_service else {},
                y=21,
            ),
            "view": _widget(
                _REFRESH_VIEW_TITLE, {"type": "linked_view", "view_name": _PLAIN_VIEW}, {}, y=41
            ),
        },
    ) as dashboard:
        yield dashboard


def _wait_until_drawn(widget: DashboardGraphWidget) -> str:
    """Wait for the widget to draw its first window, and return its graph time."""
    expect(
        widget.timestamp, f"Widget '{widget.widget_title}' never showed its graph time"
    ).not_to_be_empty()
    return widget.timestamp.inner_text()


def _expect_moved_to_the_picked_window(widget: DashboardGraphWidget, window_before: str) -> None:
    expect(
        widget.timestamp,
        f"Widget '{widget.widget_title}' kept its window although the dashboard's changed",
    ).not_to_have_text(window_before)
    expect(
        widget.timestamp,
        f"Widget '{widget.widget_title}' moved its window but not to the picked range",
    ).to_contain_text(_TWO_DATE_WINDOW)


def _expect_dashboard_took_the_gesture(
    time_picker: GlobalTimePicker,
    range_before: str,
    sibling: DashboardGraphWidget,
    sibling_axis_before: list[str],
    gesture: str,
) -> None:
    """Expect the picker to show the gesture's window as a custom range, and the other widget
    following the dashboard to have redrawn.

    The time axis rather than the graph time judges the sibling: a zoom within the hour can
    keep the same date and step, and so the same graph time.
    """
    expect(
        time_picker.dropdown_selection,
        f"The picker still shows a preset although the {gesture} made the window a custom one",
    ).to_have_text(_CUSTOM_RANGE)
    expect(
        time_picker.trigger, f"The picker did not show the window the {gesture} moved to"
    ).not_to_have_text(range_before)
    expect(
        sibling.graph.time_axis_labels,
        f"The other following widget kept its window after the {gesture}",
    ).not_to_have_text(sibling_axis_before)


def test_header_carries_the_only_global_time_picker(
    inheriting_dashboard: CustomDashboard, javascript_errors: list[str]
) -> None:
    """The dashboard's header carries its time picker, and no widget carries one of its own."""
    first, second = (
        DashboardGraphWidget(inheriting_dashboard, title) for title in _INHERITING_WIDGET_TITLES
    )

    _wait_until_drawn(first)
    _wait_until_drawn(second)

    expect(
        inheriting_dashboard.header_time_picker,
        "The dashboard header did not render exactly one global time picker",
    ).to_have_count(1)
    expect(
        GlobalTimePicker(inheriting_dashboard.main_area).root,
        "A widget rendered a global time picker beside the one in the header",
    ).to_have_count(1)
    assert not javascript_errors, f"JavaScript errors were raised: {javascript_errors}"


def test_preset_selection_redraws_every_inheriting_widget_in_place(
    inheriting_dashboard: CustomDashboard, javascript_errors: list[str]
) -> None:
    """One preset picked in the header drives every widget following the dashboard's range,
    which redraw in place.
    """
    first, second = (
        DashboardGraphWidget(inheriting_dashboard, title) for title in _INHERITING_WIDGET_TITLES
    )
    first_before = _wait_until_drawn(first)
    second_before = _wait_until_drawn(second)
    time_picker = GlobalTimePicker(inheriting_dashboard.main_area)
    _mark_document(inheriting_dashboard)

    time_picker.select_preset(OTHER_PRESET)

    _expect_moved_to_the_picked_window(first, first_before)
    _expect_moved_to_the_picked_window(second, second_before)
    expect(
        time_picker.dropdown_selection,
        "The picker did not show the range that was just picked as the active one",
    ).to_have_text(OTHER_PRESET)
    assert _document_survived(inheriting_dashboard), (
        "Picking a range reloaded the dashboard instead of redrawing its widgets"
    )
    assert not javascript_errors, f"JavaScript errors were raised: {javascript_errors}"


def test_overriding_widget_keeps_its_own_range(
    mixed_time_range_dashboard: CustomDashboard, javascript_errors: list[str]
) -> None:
    """A preset picked in the header moves only the widgets following the dashboard's range.

    The overriding widget is judged once the following one has redrawn: both would have
    refetched off the same change.
    """
    following = DashboardGraphWidget(mixed_time_range_dashboard, _INHERITING_WIDGET_TITLE)
    overriding = DashboardGraphWidget(mixed_time_range_dashboard, _OVERRIDING_WIDGET_TITLE)
    following_before = _wait_until_drawn(following)
    overriding_before = _wait_until_drawn(overriding)

    GlobalTimePicker(mixed_time_range_dashboard.main_area).select_preset(OTHER_PRESET)

    _expect_moved_to_the_picked_window(following, following_before)
    expect(
        overriding.timestamp,
        "The widget with its own range followed the dashboard's instead",
    ).to_have_text(overriding_before)
    assert not javascript_errors, f"JavaScript errors were raised: {javascript_errors}"


def test_zooming_a_following_widget_zooms_the_dashboard(
    zoom_dashboard: CustomDashboard, javascript_errors: list[str]
) -> None:
    """A zoom in a widget following the dashboard is committed to the dashboard's range, which
    the widget with its own range does not follow.
    """
    gestured, sibling = (
        DashboardGraphWidget(zoom_dashboard, title) for title in _INHERITING_WIDGET_TITLES
    )
    overriding = DashboardGraphWidget(zoom_dashboard, _OVERRIDING_WIDGET_TITLE)
    _wait_until_drawn(gestured)
    _wait_until_drawn(sibling)
    overriding_window = _wait_until_drawn(overriding)
    time_picker = GlobalTimePicker(zoom_dashboard.main_area)
    range_before = time_picker.trigger.inner_text()
    sibling_axis_before = sibling.graph.time_axis_label_texts()
    _mark_document(zoom_dashboard)

    gestured.graph.drag_across_canvas(0.3, 0.7)

    _expect_dashboard_took_the_gesture(
        time_picker, range_before, sibling, sibling_axis_before, "zoom"
    )
    expect(overriding.timestamp, "The widget with its own range followed the zoom").to_have_text(
        overriding_window
    )
    assert _document_survived(zoom_dashboard), (
        "The zoom reloaded the dashboard instead of redrawing its widgets"
    )
    assert not javascript_errors, f"JavaScript errors were raised: {javascript_errors}"


def test_resetting_the_zoom_returns_the_dashboard_to_its_preset(
    zoom_dashboard: CustomDashboard, javascript_errors: list[str]
) -> None:
    """Resetting a zoom in a widget following the dashboard returns the dashboard's range to the
    preset it started on.
    """
    gestured, sibling = (
        DashboardGraphWidget(zoom_dashboard, title) for title in _INHERITING_WIDGET_TITLES
    )
    overriding = DashboardGraphWidget(zoom_dashboard, _OVERRIDING_WIDGET_TITLE)
    _wait_until_drawn(gestured)
    _wait_until_drawn(sibling)
    overriding_window = _wait_until_drawn(overriding)
    time_picker = GlobalTimePicker(zoom_dashboard.main_area)
    preset_before = time_picker.dropdown_selection.inner_text()
    range_before = time_picker.trigger.inner_text()
    sibling_axis_before = sibling.graph.time_axis_label_texts()
    gestured.graph.drag_across_canvas(0.3, 0.7)
    _expect_dashboard_took_the_gesture(
        time_picker, range_before, sibling, sibling_axis_before, "zoom"
    )
    zoomed_range = time_picker.trigger.inner_text()
    sibling_axis_zoomed = sibling.graph.time_axis_label_texts()

    gestured.graph.reset_zoom_button.click()

    expect(
        time_picker.dropdown_selection,
        "Resetting the zoom did not return the picker to the preset it started on",
    ).to_have_text(preset_before)
    expect(
        time_picker.trigger, "The picker kept the zoomed window although the zoom was reset"
    ).not_to_have_text(zoomed_range)
    expect(
        sibling.graph.time_axis_labels,
        "The other following widget kept the zoomed window although the zoom was reset",
    ).not_to_have_text(sibling_axis_zoomed)
    expect(overriding.timestamp, "The widget with its own range followed the reset").to_have_text(
        overriding_window
    )
    assert not javascript_errors, f"JavaScript errors were raised: {javascript_errors}"


def test_panning_a_following_widget_pans_the_dashboard(
    zoom_dashboard: CustomDashboard, javascript_errors: list[str]
) -> None:
    """A pan in a widget following the dashboard is committed to the dashboard's range, which
    the widget with its own range does not follow.
    """
    gestured, sibling = (
        DashboardGraphWidget(zoom_dashboard, title) for title in _INHERITING_WIDGET_TITLES
    )
    overriding = DashboardGraphWidget(zoom_dashboard, _OVERRIDING_WIDGET_TITLE)
    _wait_until_drawn(gestured)
    _wait_until_drawn(sibling)
    overriding_window = _wait_until_drawn(overriding)
    time_picker = GlobalTimePicker(zoom_dashboard.main_area)
    range_before = time_picker.trigger.inner_text()
    sibling_axis_before = sibling.graph.time_axis_label_texts()
    _mark_document(zoom_dashboard)

    gestured.graph.drag_axis_strip(0.6, 0.3)

    _expect_dashboard_took_the_gesture(
        time_picker, range_before, sibling, sibling_axis_before, "pan"
    )
    expect(overriding.timestamp, "The widget with its own range followed the pan").to_have_text(
        overriding_window
    )
    assert _document_survived(zoom_dashboard), (
        "The pan reloaded the dashboard instead of redrawing its widgets"
    )
    assert not javascript_errors, f"JavaScript errors were raised: {javascript_errors}"


@pytest.mark.skip_if_edition("cloud")(
    reason="The preference is set on ADMIN_USER, but the cloud browser signs in as the IdP's user"
)
@pytest.mark.usefixtures("preferred_default_range")
def test_user_preference_preselects_the_dashboard_range(
    inheriting_dashboard: CustomDashboard, javascript_errors: list[str]
) -> None:
    """The user's preferred default range is the one a dashboard's picker opens on, and the
    widgets following the dashboard draw it.
    """
    expect(
        GlobalTimePicker(inheriting_dashboard.main_area).dropdown_selection,
        "The picker opened on a range other than the user's preferred default",
    ).to_have_text(OTHER_PRESET)
    first, second = (
        DashboardGraphWidget(inheriting_dashboard, title) for title in _INHERITING_WIDGET_TITLES
    )
    expect(
        first.timestamp,
        f"Widget '{first.widget_title}' drew a narrower window than the range preselected",
    ).to_contain_text(_TWO_DATE_WINDOW)
    expect(
        second.timestamp,
        f"Widget '{second.widget_title}' drew a narrower window than the range preselected",
    ).to_contain_text(_TWO_DATE_WINDOW)
    assert not javascript_errors, f"JavaScript errors were raised: {javascript_errors}"


def test_view_widget_follows_the_dashboard_range_without_reloading(
    view_dashboard: CustomDashboard, javascript_errors: list[str]
) -> None:
    """A classic view widget takes a range picked in the header from a message, in place.

    The view renders in an iframe whose URL carries no range: the dashboard posts each range
    to the iframe's page, which hands it to the engine graphs the view mounts.
    """
    widget = view_dashboard.get_widget(_VIEW_WIDGET_TITLE)
    iframe = widget.locator("iframe")
    view_document = widget.frame_locator("iframe").locator("html")
    panel = GraphPanel(
        GraphAccessor(view_dashboard)
        .graph_root(GraphContainment.DASHBOARD_WIDGET, widget=widget, iframed=True)
        .first,
        view_dashboard.page,
        view_dashboard.main_area,
    )
    expect(panel.timestamp, "The view never showed the time of its graph").not_to_be_empty()
    window_before = panel.timestamp.inner_text()
    src_before = iframe.get_attribute("src")
    view_document.evaluate("() => { window.__cmkDashboardTimeControlsMarker = true }")
    view_document.evaluate(_RECORD_MESSAGES)

    GlobalTimePicker(view_dashboard.main_area).select_preset(OTHER_PRESET)

    expect(
        panel.timestamp, "The view's graph kept its window although the dashboard's changed"
    ).not_to_have_text(window_before)
    expect(
        panel.timestamp, "The view's graph moved its window but not to the picked range"
    ).to_contain_text(_TWO_DATE_WINDOW)
    wait_until(
        lambda: view_document.evaluate(_LONGEST_POSTED_RANGE) >= _OTHER_PRESET_SECONDS,
        timeout=10,
        condition_name="the dashboard to post the picked range to the view",
    )
    assert iframe.get_attribute("src") == src_before, (
        "The dashboard handed the view the range through its URL instead of a message"
    )
    assert view_document.evaluate("() => window.__cmkDashboardTimeControlsMarker === true"), (
        "Picking a range reloaded the view's document instead of redrawing it"
    )
    assert not javascript_errors, f"JavaScript errors were raised: {javascript_errors}"


@pytest.mark.parametrize("widget", _TIME_RANGE_WIDGETS)
def test_new_widget_follows_the_dashboard_and_offers_its_own_ranges(
    widget: _TimeRangeWidget,
    linux_hosts: list[str],
    cloned_linux_hosts_dashboard: CustomDashboard,
) -> None:
    """A new widget follows the dashboard's range, and a separate range is picked from the
    widget's own selector, with the ranges it offered before following was possible.
    """
    wizard = _open_new_widget_time_settings(cloned_linux_hosts_dashboard, linux_hosts[0], widget)
    time_settings = wizard.time_range_settings
    expect(
        time_settings.follow_dashboard_radio, "A new widget does not follow the dashboard"
    ).to_be_checked()
    expect(
        time_settings.range_selector,
        "A widget following the dashboard offers a range of its own",
    ).to_have_count(0)

    time_settings.separate_range_radio.click()
    wizard.expand_collapsed_panels()

    assert time_settings.offered_ranges() == _GRAPH_WIDGET_RANGES, (
        "A separate range does not offer the ranges the widget offered before"
    )
    expect(
        wizard.locator().get_by_text(_LEGACY_FIXED_TIMERANGE),
        "The wizard still offers the legacy option not to follow time range changes",
    ).to_have_count(0)


@pytest.mark.parametrize("widget", _TIME_RANGE_WIDGETS)
def test_separate_widget_range_is_kept_across_a_reload(
    widget: _TimeRangeWidget,
    linux_hosts: list[str],
    cloned_linux_hosts_dashboard: CustomDashboard,
) -> None:
    """A widget saved with a separate range opens on that range again after a reload."""
    wizard = _open_new_widget_time_settings(cloned_linux_hosts_dashboard, linux_hosts[0], widget)
    wizard.time_range_settings.separate_range_radio.click()
    wizard.time_range_settings.select_range(_OVERRIDE_RANGE)
    expect(wizard.preview_title, "The preview never titled the widget").not_to_be_empty()
    widget_title = wizard.preview_title.inner_text().strip()
    wizard.add_and_place_widget_button.click()
    cloned_linux_hosts_dashboard.save_widgets()

    cloned_linux_hosts_dashboard.navigate()
    cloned_linux_hosts_dashboard.enter_edit_widgets_mode()
    wizard = cloned_linux_hosts_dashboard.open_edit_widget_sidebar(
        MetricsAndGraphsWidgetWizard, widget_title
    )
    wizard.next_step_visualization_button.click()

    expect(
        wizard.time_range_settings.separate_range_radio,
        "The widget saved with a separate range follows the dashboard after a reload",
    ).to_be_checked()
    wait_until(
        lambda: wizard.time_range_settings.selected_range() == _OVERRIDE_RANGE,
        timeout=10,
        condition_name=f"the widget saved with a separate range to show {_OVERRIDE_RANGE!r}",
    )


class _RecordedRequests:
    """The data requests of each refresh path, with when they were sent."""

    def __init__(self, page: Page, figure: _FigureWidget) -> None:
        self._page = page
        self._figure = figure
        self.sent: dict[str, list[tuple[float, Request]]] = {"graph": [], "figure": [], "view": []}

    def __call__(self, request: Request) -> None:
        if (kind := self._kind(request)) is not None:
            self.sent[kind].append((time.monotonic(), request))

    def _kind(self, request: Request) -> str | None:
        if request.frame != self._page.main_frame:
            # The view's page refetches its content with the content-only display options,
            # which its first load does not carry.
            if "widget_iframe_view.py" in request.url and "_display_options=" in request.url:
                return "view"
            return None
        if request.url.endswith("/domain-types/graph/actions/fetch_data/invoke"):
            return "graph"
        if request.url.endswith(self._figure.compute_endpoint):
            return "figure"
        return None

    def every_path_refetched(self) -> bool:
        return all(self.sent.values())

    def first_refetch(self) -> float:
        return min(sent[0][0] for sent in self.sent.values())

    def counts(self) -> dict[str, int]:
        return {kind: len(sent) for kind, sent in self.sent.items()}

    def urls(self) -> dict[str, list[str]]:
        return {kind: [request.url for _, request in sent] for kind, sent in self.sent.items()}

    def last(self, kind: str) -> Request | None:
        return self.sent[kind][-1][1] if self.sent[kind] else None

    def clear(self) -> None:
        for sent in self.sent.values():
            sent.clear()


def _wait_until_rendered(dashboard: CustomDashboard) -> DashboardGraphWidget:
    """Wait for the graph and the view to render and the figure's first compute to settle,
    then return the graph widget."""
    graph = DashboardGraphWidget(dashboard, _REFRESH_GRAPH_TITLE)
    expect(graph.timestamp, "The graph widget never rendered").not_to_be_empty()
    expect(
        dashboard.get_widget(_REFRESH_VIEW_TITLE)
        .frame_locator("iframe")
        .locator("#data_container"),
        "The view widget never rendered",
    ).to_be_visible()
    # The figure renders nothing a locator could wait for across both figure types; its
    # first compute request settling stands in for it.
    dashboard.page.wait_for_load_state("networkidle")
    return graph


def _wait_for_every_path(
    page: Page, requests: _RecordedRequests, *, timeout: float, failure: str
) -> None:
    """Wait for every refresh path to have sent a request.

    Waited out through Playwright rather than `wait_until`: the sync API only hands over the
    requests it saw while one of its own calls runs, never during a `time.sleep`.
    """
    deadline = time.monotonic() + timeout
    while not requests.every_path_refetched():
        assert time.monotonic() < deadline, f"{failure}: {requests.counts()}"
        page.wait_for_timeout(_POLL_MS)


@pytest.mark.parametrize("figure", _REFRESHING_FIGURES)
def test_every_widget_refetches_its_data_once_per_refresh_interval(
    figure: _FigureWidget, refresh_dashboard: CustomDashboard, javascript_errors: list[str]
) -> None:
    """Each refresh tick has every widget fetch its data again, once.

    One widget per refresh path: the graph fetches its data, the figure asks its compute
    endpoint, and the view, told of the tick by a message to its iframe, reloads its content
    there. Real timers, as the view's page runs a clock of its own: only requests sent after
    the widgets rendered are counted, and the count is closed before the next tick.
    """
    page = refresh_dashboard.page
    expect(
        refresh_dashboard.refresh_control,
        "The dashboard does not refresh live every 30 seconds",
    ).to_contain_text(f"{_REFRESH_INTERVAL_SECONDS} sec")
    _wait_until_rendered(refresh_dashboard)
    requests = _RecordedRequests(page, figure)
    page.on("request", requests)

    try:
        _wait_for_every_path(
            page,
            requests,
            timeout=_REFRESH_INTERVAL_SECONDS + _TICK_ANSWER_SECONDS,
            failure="Not every widget refetched within one refresh interval",
        )
        # Up to just before the next tick: a second request by then is a refetch too many.
        count_closes = (
            requests.first_refetch() + _REFRESH_INTERVAL_SECONDS - _NEXT_TICK_MARGIN_SECONDS
        )
        page.wait_for_timeout(max(0.0, count_closes - time.monotonic()) * 1000)
    finally:
        page.remove_listener("request", requests)

    assert requests.counts() == {"graph": 1, "figure": 1, "view": 1}, (
        f"A widget did not refetch exactly once in one refresh interval: {requests.urls()}"
    )
    assert not javascript_errors, f"JavaScript errors were raised: {javascript_errors}"


def _apply_range_ending_an_hour_ago(dashboard: CustomDashboard) -> float:
    """Apply a two-hour custom range ending an hour ago; return where it ends, in epoch
    seconds."""
    _start_epoch, start = _browser_moment_ago(dashboard.page, 3 * 60 * 60)
    end_epoch, end = _browser_moment_ago(dashboard.page, 60 * 60)
    GlobalTimePicker(dashboard.main_area).apply_custom_range(start, end)
    return end_epoch


@pytest.mark.parametrize("figure", _REFRESHING_FIGURES)
def test_a_past_range_pauses_the_refresh(
    figure: _FigureWidget, refresh_dashboard: CustomDashboard, javascript_errors: list[str]
) -> None:
    """A custom range that already ended cannot gain data, so it stops the live refresh."""
    page = refresh_dashboard.page
    expect(
        refresh_dashboard.refresh_control, "The dashboard does not start out refreshing live"
    ).to_contain_text(f"{_REFRESH_INTERVAL_SECONDS} sec")
    _wait_until_rendered(refresh_dashboard)
    _apply_range_ending_an_hour_ago(refresh_dashboard)
    expect(
        refresh_dashboard.refresh_control.get_by_role("button", name="Resume live refresh"),
        "A range that already ended left the refresh running",
    ).to_be_visible()
    # The fetches of the picked window itself are not refreshes.
    page.wait_for_load_state("networkidle")
    requests = _RecordedRequests(page, figure)
    page.on("request", requests)

    try:
        # One interval and then some: a tick still running would have fired by then.
        page.wait_for_timeout((_REFRESH_INTERVAL_SECONDS + _NEXT_TICK_MARGIN_SECONDS) * 1000)
    finally:
        page.remove_listener("request", requests)

    assert requests.counts() == {"graph": 0, "figure": 0, "view": 0}, (
        f"A widget refetched although the refresh is paused: {requests.urls()}"
    )
    assert not javascript_errors, f"JavaScript errors were raised: {javascript_errors}"


# Only the widgets taking the dashboard's range: the host statistics figure computes over no
# range, and the view's rows are server-rendered without one.
_RANGED_FIGURES: Final = [param for param in _REFRESHING_FIGURES if param.id == "single_metric"]


@pytest.mark.parametrize("figure", _RANGED_FIGURES)
def test_a_past_range_is_fetched_as_picked(
    figure: _FigureWidget, refresh_dashboard: CustomDashboard, javascript_errors: list[str]
) -> None:
    """The widgets following the dashboard fetch the past range that was picked."""
    page = refresh_dashboard.page
    _wait_until_rendered(refresh_dashboard)
    requests = _RecordedRequests(page, figure)
    page.on("request", requests)

    try:
        end_epoch = _apply_range_ending_an_hour_ago(refresh_dashboard)
        page.wait_for_load_state("networkidle")
    finally:
        page.remove_listener("request", requests)

    graph_request = requests.last("graph")
    assert graph_request is not None, "The graph widget did not fetch the picked range"
    graph_end = _requested_window_end(graph_request, "requested_time_range")
    assert isinstance(graph_end, int | float), f"The graph's window end is {graph_end!r}"
    assert end_epoch <= graph_end <= end_epoch + _FETCH_ALIGNMENT_SECONDS, (
        f"The graph widget fetched a window ending at {graph_end}, not at the picked {end_epoch}"
    )
    figure_request = requests.last("figure")
    assert figure_request is not None, "The figure widget did not compute the picked range"
    figure_end = _requested_window_end(figure_request, "time_range")
    assert isinstance(figure_end, str), f"The figure's window end is {figure_end!r}"
    assert datetime.fromisoformat(figure_end).timestamp() == end_epoch, (
        f"The figure widget computed a window ending at {figure_end}, not at the picked {end_epoch}"
    )
    assert not javascript_errors, f"JavaScript errors were raised: {javascript_errors}"


def _zoom(graph: DashboardGraphWidget) -> None:
    graph.graph.drag_across_canvas(0.3, 0.7)


def _pan(graph: DashboardGraphWidget) -> None:
    graph.graph.drag_axis_strip(0.6, 0.3)


@pytest.mark.parametrize("figure", _REFRESHING_FIGURES)
@pytest.mark.parametrize("gesture", [pytest.param(_zoom, id="zoom"), pytest.param(_pan, id="pan")])
def test_a_graph_gesture_pauses_the_refresh_until_resumed(
    gesture: Callable[[DashboardGraphWidget], None],
    figure: _FigureWidget,
    refresh_dashboard: CustomDashboard,
    javascript_errors: list[str],
) -> None:
    """Zooming or panning a graph picks a window of its own, which holds until Resume.

    The gesture becomes the dashboard's range and pauses the refresh, so the window the user
    is looking at stays put: no widget refreshes until Resume, which then refreshes them all.
    """
    page = refresh_dashboard.page
    expect(
        refresh_dashboard.refresh_control, "The dashboard does not start out refreshing live"
    ).to_contain_text(f"{_REFRESH_INTERVAL_SECONDS} sec")
    graph = _wait_until_rendered(refresh_dashboard)
    resume = refresh_dashboard.refresh_control.get_by_role("button", name="Resume live refresh")

    gesture(graph)

    expect(resume, "The gesture left the refresh running").to_be_visible()
    # The fetches of the gesture's window itself are not refreshes.
    page.wait_for_load_state("networkidle")
    requests = _RecordedRequests(page, figure)
    page.on("request", requests)
    try:
        # One interval and then some: a tick still running would have fired by then.
        page.wait_for_timeout((_REFRESH_INTERVAL_SECONDS + _NEXT_TICK_MARGIN_SECONDS) * 1000)
        assert requests.counts() == {"graph": 0, "figure": 0, "view": 0}, (
            f"A widget refreshed after the gesture, before Resume: {requests.urls()}"
        )
        resume.click()
        _wait_for_every_path(
            page,
            requests,
            timeout=_TICK_ANSWER_SECONDS,
            failure="Not every widget refreshed once Resume was clicked",
        )
    finally:
        page.remove_listener("request", requests)

    assert not javascript_errors, f"JavaScript errors were raised: {javascript_errors}"
