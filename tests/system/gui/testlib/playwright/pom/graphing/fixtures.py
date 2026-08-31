#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Reusable fixtures for the graph E2E suites.

Registered for discovery in ``tests/system/gui/conftest.py``.
"""

from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from typing import Final, NamedTuple

import pytest
from playwright.sync_api import Page

from tests.system.gui.testlib.playwright.pom.graphing.dashboard_graph_widget import (
    DashboardGraphWidget,
)
from tests.system.gui.testlib.playwright.pom.graphing.graph_surfaces import GraphSurface
from tests.system.gui.testlib.playwright.pom.graphing.service_graphs_hover_popup import (
    ServiceGraphsHoverPopup,
)
from tests.system.gui.testlib.playwright.pom.graphing.timeseries_graph import ServiceGraphs
from tests.system.gui.testlib.playwright.pom.monitor.combined_graph import (
    CombinedGraphsServiceSearch,
)
from tests.system.gui.testlib.playwright.pom.monitor.custom_dashboard import CustomDashboard
from tests.system.gui.testlib.playwright.pom.monitor.dashboard import MainDashboard
from tests.system.gui.testlib.playwright.pom.monitor.hosts_dashboard import LinuxHostsDashboard
from tests.system.gui.testlib.playwright.pom.monitor.service import ServicePage
from tests.system.gui.testlib.playwright.pom.monitor.service_search import ServiceSearchPage
from tests.system.gui.testlib.playwright.pom.monitor.services_of_host import ServicesOfHostPage
from tests.system.gui.testlib.playwright.timeouts import TIMEOUT_SLOW_DASHBOARD_LOAD_MS
from tests.testlib.common.utils2 import is_cleanup_enabled
from tests.testlib.graphing import InjectedRrd
from tests.testlib.site import ADMIN_USER, Site

# Several multi-series graphs on one page, which the "every graph" and tooltip tests need.
SERVICE_WITH_GRAPHS = "Memory"

# The combined page folds services into one card per matched graph template, so only a
# filter spanning several templates leaves a test more than one card to judge. A linux dump
# host's cpu services carry two.
COMBINED_GRAPHS_SERVICE_FILTER = "cpu"

# The built-in Linux hosts dashboard already carries a scatterplot widget - the agent
# execution time over the hosts' Check_MK services - so that surface needs no dashboard of
# its own.
SCATTERPLOT_WIDGET_TITLE = "Total agent execution time"

# The collection every user starts out with; adding to it clones it for the acting user.
_BUILTIN_COLLECTION_NAME: Final = "default"
_BUILTIN_COLLECTION_TITLE: Final = "My graphs"

_COLLECTION_FAMILY: Final = "graph_collection"
_COLLECTION_USER_CONFIG: Final = "user_graph_collections.mk"
GRAPH_COLLECTION_SIZE: Final = 2


@pytest.fixture(name="graph_hosts_with_varying_data", scope="module")
def fixture_graph_hosts_with_varying_data(linux_hosts: list[str]) -> list[str]:
    """Hosts whose real agent data yields graphs with varying values."""
    return linux_hosts


@pytest.fixture(name="graph_hosts_high_density", scope="module")
def fixture_graph_hosts_high_density(test_site: Site) -> list[str]:
    """Monitored hosts/services with high-density graph data.

    For performance/loading/legend/tooltip cases: a graph near the engine's
    ceiling (~1M points) and/or many series (200+ metrics). `inject_rrd` covers
    the point-count dimension (it writes one series); the many-series dimension
    needs a host carrying many real metrics.
    """
    pytest.skip("graph_hosts_high_density is scaffolding: seed a high-density monitored service.")


@pytest.fixture(name="graph_rrd_with_gaps", scope="module")
def fixture_graph_rrd_with_gaps(test_site: Site) -> InjectedRrd:
    """An RRD with missing samples; inject via `graphing.inject_rrd` (GAPS)."""
    pytest.skip("graph_rrd_with_gaps is scaffolding: bind inject_rrd to a monitored service.")


@pytest.fixture(name="graph_rrd_dst_boundary", scope="module")
def fixture_graph_rrd_dst_boundary(test_site: Site) -> InjectedRrd:
    """An RRD whose rendered window crosses a DST transition.

    DST is a timezone/window concern, not a data shape: set the user timezone to
    a DST-observing zone (e.g. Europe/Berlin) and inject `VARYING` data starting
    at `graphing.DST_FALL_BACK_BERLIN_UTC`, bound to a monitored service.
    Use the fall-back instant: it makes local 02:00-02:59 occur twice, which is
    what the "no duplicate X-axis labels" regression (Werk #14830) needs;
    spring-forward only skips the hour and would not exercise it.
    """
    pytest.skip("graph_rrd_dst_boundary is scaffolding: see docstring.")


class RrdMetric(NamedTuple):
    """A metric under both the names it goes by."""

    name: str  # what the RRD and the REST API call it, e.g. "mem_used"
    title: str  # what the GUI labels it, e.g. "RAM used"


class RrdMetricSource(NamedTuple):
    """A monitored service and the metrics it stores RRD data for."""

    host_name: str
    service_name: str
    metrics: Sequence[RrdMetric]


@pytest.fixture(name="rrd_metric_source", scope="module")
def fixture_rrd_metric_source(
    test_site: Site, graph_hosts_with_varying_data: list[str]
) -> RrdMetricSource:
    """Metrics a monitored service actually reports, read from the site rather than hard-coded.

    Both names are collected: the REST API builds a graph out of metric names, while the
    designer's dropdown only ever offers their titles.

    Two metrics are needed: a graph that stays interesting when a second one joins it.
    """
    host_name = graph_hosts_with_varying_data[0]
    metric_names = test_site.live.query_value(
        f"GET services\nColumns: metrics\n"
        f"Filter: host_name = {host_name}\nFilter: description = {SERVICE_WITH_GRAPHS}\n"
    )
    titles = test_site.openapi.autocomplete.metric_titles(host_name, SERVICE_WITH_GRAPHS)
    metrics = [RrdMetric(str(name), titles[str(name)]) for name in metric_names if name in titles]
    if len(metrics) < 2:
        pytest.skip(
            f"Service {SERVICE_WITH_GRAPHS!r} on {host_name!r} offers "
            f"{len(metrics)} named metrics; two are needed."
        )
    return RrdMetricSource(host_name, SERVICE_WITH_GRAPHS, metrics)


@contextmanager
def _as_admin_user(test_site: Site) -> Iterator[None]:
    """Act as the user the browser logs in as, not the site's automation user.

    Custom graphs are stored per user and created private, so a graph made through the
    site's own session would belong to `AUTOMATION_USER` and be invisible to the
    `ADMIN_USER` the tests drive - the designer would only ever find a 404.
    """
    session = test_site.openapi
    automation_auth = session.headers["Authorization"]
    session.set_authentication_header(ADMIN_USER, test_site.admin_password)
    try:
        yield
    finally:
        session.headers["Authorization"] = automation_auth


@contextmanager
def _custom_graph(
    test_site: Site, name: str, title: str, data_sources: Sequence[Mapping[str, object]]
) -> Iterator[str]:
    with _as_admin_user(test_site):
        test_site.openapi.custom_graph.create(name, title, data_sources)
    try:
        yield name
    finally:
        # Deleted even when the site is kept for inspection: the graphs are named per
        # fixture, so one left behind makes the next test's creation collide with it.
        with _as_admin_user(test_site):
            test_site.openapi.custom_graph.delete(name)


@pytest.fixture(name="saved_custom_graph")
def fixture_saved_custom_graph(
    test_site: Site, rrd_metric_source: RrdMetricSource
) -> Iterator[str]:
    """A saved custom graph holding one RRD metric of a monitored service.

    Created over the REST API rather than through the designer, so the tests that read a
    saved graph do not fail on a broken designer.
    """
    data_source = test_site.openapi.custom_graph.rrd_metric_data_source(
        "A",
        rrd_metric_source.host_name,
        rrd_metric_source.service_name,
        rrd_metric_source.metrics[0].name,
    )
    with _custom_graph(test_site, "e2e_saved_graph", "E2E saved graph", [data_source]) as name:
        yield name


@pytest.fixture(name="custom_graph_for_editing")
def fixture_custom_graph_for_editing(test_site: Site) -> Iterator[str]:
    """An empty saved custom graph to open in the designer's edit mode.

    The designer page takes the graph to edit as a mandatory URL parameter, so even the
    "build a graph from scratch" cases need one to exist first.
    """
    with _custom_graph(test_site, "e2e_designer_graph", "E2E designer graph", []) as name:
        yield name


@pytest.fixture(name="graph_collection")
def fixture_graph_collection(
    test_site: Site, graph_hosts_with_varying_data: list[str]
) -> Iterator[str]:
    """The title of a saved graph collection holding `GRAPH_COLLECTION_SIZE` graphs.

    Filled acting as the user the browser logs in as: the graphs land in that user's own copy of
    the collection, and only that user sees them.

    Collections are a Pro+ surface, so a test asking for this gates its own edition.
    """
    host_name = graph_hosts_with_varying_data[0]
    discovered = test_site.openapi.graph.discover_template_graphs(host_name, SERVICE_WITH_GRAPHS)
    addable_graphs = [
        graph for graph in discovered["graphs"] if graph["add_to_specification"] is not None
    ]
    assert len(addable_graphs) >= GRAPH_COLLECTION_SIZE, (
        f"{host_name}/{SERVICE_WITH_GRAPHS} yielded {len(addable_graphs)} graphs that can be "
        f"added, too few to fill a collection of {GRAPH_COLLECTION_SIZE}: "
        f"{discovered['no_data_message']}"
    )

    # The add appends, so a collection left behind by a killed run would grow instead of match.
    collections_of_user = f"var/check_mk/web/{ADMIN_USER}/{_COLLECTION_USER_CONFIG}"
    test_site.delete_file(collections_of_user)
    try:
        with test_site.openapi.acting_as(ADMIN_USER, test_site.admin_password):
            for graph in addable_graphs[:GRAPH_COLLECTION_SIZE]:
                test_site.openapi.graph.add_to_container(
                    family=_COLLECTION_FAMILY,
                    container_id=_BUILTIN_COLLECTION_NAME,
                    specification=graph["add_to_specification"],
                    internal=graph["internal"],
                )
        yield _BUILTIN_COLLECTION_TITLE
    finally:
        test_site.delete_file(collections_of_user)


@pytest.fixture(name="javascript_errors")
def fixture_javascript_errors(dashboard_page: MainDashboard) -> Iterator[list[str]]:
    """Uncaught page errors raised while the test runs."""
    errors: list[str] = []
    dashboard_page.page.on("pageerror", lambda error: errors.append(str(error)))
    yield errors


@pytest.fixture(name="requested_urls")
def fixture_requested_urls(dashboard_page: MainDashboard) -> Iterator[list[str]]:
    """Every URL the page requested while the test runs.

    A passive listener, not a `page.route` handler: routing intercepts what it matches, and
    every intercepted request then has to be continued by hand.
    """
    urls: list[str] = []
    dashboard_page.page.on("request", lambda request: urls.append(request.url))
    yield urls


def open_service_graphs(page: Page, host_name: str) -> ServiceGraphs:
    """Open the service detail page holding the graphs and wait for them to render.

    Public because `ServicePage.navigate` cannot be: a service page is reached through the
    host's service list rather than by a route of its own, so a test returning to it after
    navigating away has to walk the same list again.
    """
    services_of_host = ServicesOfHostPage(page, host_name=host_name)
    services_of_host.services_table.host_services_table(host_name).get_by_role(
        "link", name=SERVICE_WITH_GRAPHS, exact=True
    ).click()
    graphs = ServiceGraphs(
        ServicePage(
            page,
            host_name=host_name,
            service_name=SERVICE_WITH_GRAPHS,
            navigate_to_page=False,
        )
    )
    graphs.wait_until_rendered()
    return graphs


@pytest.fixture(name="service_graphs")
def fixture_service_graphs(
    dashboard_page: MainDashboard,
    graph_hosts_with_varying_data: list[str],
    javascript_errors: list[str],
    requested_urls: list[str],
) -> Iterator[ServiceGraphs]:
    """The graph panels on a service detail page, rendered and ready for interaction.

    Depends on `javascript_errors` and `requested_urls` so their listeners are attached
    before this navigates.
    """
    yield open_service_graphs(dashboard_page.page, graph_hosts_with_varying_data[0])


@pytest.fixture(name="service_graphs_hover_popup")
def fixture_service_graphs_hover_popup(
    dashboard_page: MainDashboard,
    graph_hosts_with_varying_data: list[str],
    javascript_errors: list[str],
    requested_urls: list[str],
) -> Iterator[ServiceGraphsHoverPopup]:
    """The graph hover popup off a service's graphs icon on the services-of-host view.

    Depends on `javascript_errors` and `requested_urls` so their listeners are attached
    before this navigates.
    """
    host_name = graph_hosts_with_varying_data[0]
    services = ServicesOfHostPage(dashboard_page.page, host_name=host_name)
    yield ServiceGraphsHoverPopup(services, host_name, SERVICE_WITH_GRAPHS)


@pytest.fixture(name="scatterplot_widget")
def fixture_scatterplot_widget(
    dashboard_page: MainDashboard,
    graph_hosts_with_varying_data: list[str],
    javascript_errors: list[str],
) -> Iterator[DashboardGraphWidget]:
    """The scatterplot widget of the built-in Linux hosts dashboard.

    Deliberately does not wait for the graph: whether the widget renders at all is what the
    tests judge, and waiting here would turn a failure to render into a fixture timeout
    instead of a failed assertion naming it.

    Depends on `javascript_errors` so its listener is attached before this navigates.
    """
    yield DashboardGraphWidget(LinuxHostsDashboard(dashboard_page.page), SCATTERPLOT_WIDGET_TITLE)


def _open_combined_graphs(
    dashboard_page: MainDashboard, *, host_name: str, service_filter: str | None
) -> CombinedGraphsServiceSearch:
    """Open the combined-graphs page without waiting for its cards."""
    service_search = ServiceSearchPage(dashboard_page.page)
    service_search.filter_sidebar.apply_host_filter(host_name)
    if service_filter is not None:
        service_search.filter_sidebar.apply_service_filter(service_filter)
    service_search.filter_sidebar.apply_filters(service_search.services_table)
    service_search.main_area.click_item_in_dropdown_list(
        "Services", "All metrics of same type in one graph"
    )
    return CombinedGraphsServiceSearch(service_search.page, navigate_to_page=False)


@pytest.fixture(name="combined_graphs_page")
def fixture_combined_graphs_page(
    dashboard_page: MainDashboard,
    graph_hosts_with_varying_data: list[str],
    javascript_errors: list[str],
    requested_urls: list[str],
) -> Iterator[CombinedGraphsServiceSearch]:
    """The combined-graphs page for one host's cpu services, rendered and ready.

    Depends on `javascript_errors` and `requested_urls` so their listeners are attached
    before this navigates.
    """
    combined_graphs = _open_combined_graphs(
        dashboard_page,
        host_name=graph_hosts_with_varying_data[0],
        service_filter=COMBINED_GRAPHS_SERVICE_FILTER,
    )
    combined_graphs.wait_until_rendered()
    yield combined_graphs


@pytest.fixture(name="combined_graphs_page_all_services")
def fixture_combined_graphs_page_all_services(
    dashboard_page: MainDashboard,
    graph_hosts_with_varying_data: list[str],
    javascript_errors: list[str],
) -> Iterator[CombinedGraphsServiceSearch]:
    """The combined-graphs page over every service of one host, not waiting for its cards.

    Dropping the service filter is what lets one template gather several of the host's
    services - its filesystems, its temperature zones - into a single card. A card over one
    service exercises none of the combining.

    Depends on `javascript_errors` so its listener is attached before this navigates.
    """
    yield _open_combined_graphs(
        dashboard_page, host_name=graph_hosts_with_varying_data[0], service_filter=None
    )


# Every `GraphContainment.DASHBOARD_WIDGET` surface, one widget each, on a single dashboard.
_ACTION_MENU_DASHBOARD_ID: Final = "e2e_action_menu_dashboard"
_ACTION_MENU_DASHBOARD_TITLE: Final = "E2E action menu dashboard"
_ACTION_MENU_WIDGET_TIMERANGE: Final = {"type": "graph", "duration": 14400}
_ACTION_MENU_WIDGET_SIZE: Final = {"width": 40, "height": 20}
_KNOWN_GOOD_METRIC_NAME: Final = "mem_used"


def _preferred_metric_name(metrics: Sequence[RrdMetric]) -> str:
    for metric in metrics:
        if metric.name == _KNOWN_GOOD_METRIC_NAME:
            return metric.name
    return metrics[0].name


def _relative_grid_widget(
    title: str,
    content: Mapping[str, object],
    *,
    filters: Mapping[str, object] | None = None,
    y: int,
) -> dict[str, object]:
    """One widget of a relative-grid dashboard, stacked in a single column at row `y`."""
    return {
        "general_settings": {
            "title": {"text": title, "render_mode": "with_background"},
            "render_background": True,
        },
        "content": dict(content),
        "filters": dict(filters or {}),
        "layout": {
            "type": "relative_grid",
            "position": {"x": 1, "y": y},
            "size": _ACTION_MENU_WIDGET_SIZE,
        },
    }


def _action_menu_dashboard_id(surface_key: str) -> str:
    return f"{_ACTION_MENU_DASHBOARD_ID}_{surface_key}"


def _action_menu_dashboard_title(surface_title: str) -> str:
    return f"{_ACTION_MENU_DASHBOARD_TITLE}: {surface_title}"


def _action_menu_widget_content(
    surface_key: str,
    *,
    metric_name: str,
    host_service_filters: Mapping[str, object],
    saved_custom_graph: str,
) -> tuple[Mapping[str, object], Mapping[str, object] | None]:
    """The widget `content` (and `filters`, if any) for one action-menu dashboard surface."""
    if surface_key == "dashboard_graph_widget":
        return (
            {
                "type": "custom_graph",
                "timerange": _ACTION_MENU_WIDGET_TIMERANGE,
                "graph_render_options": {},
                "custom_graph": saved_custom_graph,
            },
            None,
        )
    if surface_key == "single_timeseries_widget":
        return (
            {
                "type": "single_timeseries",
                "timerange": _ACTION_MENU_WIDGET_TIMERANGE,
                "graph_render_options": {},
                "metric": metric_name,
                "color": "default_metric",
            },
            host_service_filters,
        )
    if surface_key == "problem_percentage_widget":
        return (
            {
                "type": "problem_graph",
                "timerange": _ACTION_MENU_WIDGET_TIMERANGE,
                "graph_render_options": {},
            },
            None,
        )
    if surface_key == "alert_notification_widget":
        return (
            {
                "type": "alert_overview",
                "time_range": _ACTION_MENU_WIDGET_TIMERANGE,
                "limit_objects": 10,
            },
            None,
        )
    if surface_key == "scatterplot_widget":
        return (
            {
                "type": "average_scatterplot",
                "time_range": _ACTION_MENU_WIDGET_TIMERANGE,
                "metric": metric_name,
                "metric_color": "default",
                "average_color": "default",
                "median_color": "default",
            },
            host_service_filters,
        )
    raise ValueError(f"No action-menu widget content is defined for surface {surface_key!r}")


@pytest.fixture(name="dashboard_action_menu_surfaces")
def fixture_dashboard_action_menu_surfaces(
    surface: GraphSurface,
    test_site: Site,
    rrd_metric_source: RrdMetricSource,
    saved_custom_graph: str,
) -> Iterator[str]:
    """A single-widget custom dashboard for one `GraphContainment.DASHBOARD_WIDGET` surface.

    One dashboard per surface, rather than one dashboard shared across all five: sharing one
    meant every surface's setup had to wait for every *other* surface's widget to finish
    loading too - including the average-scatterplot widget's mean/median computation over RRD
    data, by far the slowest of the five, which pushed every surface's setup close to (and,
    for the scatterplot surface itself, past) the dashboard-load timeout.

    Built directly through the relative-grid dashboard REST endpoint rather than the "Add
    widget" wizard: two of the five surfaces (`problem_percentage_widget`,
    `alert_notification_widget`) have no wizard UI to reach at all (they live behind a
    separate, not-yet-implemented "Alerts & notifications" wizard category), so every
    widget is created the same uniform way instead of mixing that in with wizard-driven
    widgets for the rest.

    The widget's title is taken straight from `surface.title` in `graph_surfaces.py`, so a
    test resolves it with `BaseDashboard.get_widget(surface.title)` without hard-coding the
    title a second time.

    Yields the dashboard id (for `dashboard.py?name=<id>&owner=<ADMIN_USER>`, since the
    dashboard is created under `ADMIN_USER` and is private).
    """
    host_name, service_name, metrics = rrd_metric_source
    metric_name = _preferred_metric_name(metrics)
    content, filters = _action_menu_widget_content(
        surface.key,
        metric_name=metric_name,
        host_service_filters={"host": {"host": host_name}, "service": {"service": service_name}},
        saved_custom_graph=saved_custom_graph,
    )

    dashboard_id = _action_menu_dashboard_id(surface.key)
    payload = {
        "id": dashboard_id,
        "general_settings": {
            "title": {
                "text": _action_menu_dashboard_title(surface.title),
                "render": True,
                "include_context": False,
            },
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
                "share": "no",
            },
        },
        "filter_context": {
            "restricted_to_single": [],
            "filters": {},
            "mandatory_context_filters": [],
        },
        "widgets": {
            surface.key: _relative_grid_widget(surface.title, content, filters=filters, y=1)
        },
        "layout": {"type": "relative_grid"},
    }

    with _as_admin_user(test_site):
        test_site.openapi.dashboard.create_relative_grid_dashboard(payload)
    try:
        yield dashboard_id
    finally:
        if is_cleanup_enabled():
            with _as_admin_user(test_site):
                test_site.openapi.dashboard.delete(dashboard_id)


@pytest.fixture(name="dashboard_with_action_menu_widgets")
def fixture_dashboard_with_action_menu_widgets(
    dashboard_page: MainDashboard,
    dashboard_action_menu_surfaces: str,
    surface: GraphSurface,
    test_site: Site,
    javascript_errors: list[str],
) -> CustomDashboard:
    """The dashboard from `dashboard_action_menu_surfaces`, opened in the browser.

    Navigated to directly by URL rather than through 'Customize > Dashboards', matching the
    same direct-`goto` pattern other REST/file-seeded dashboard fixtures use.

    Depends on `javascript_errors` so its listener is attached before this navigates.
    """
    dashboard_page.page.goto(
        test_site.internal_url
        + f"dashboard.py?name={dashboard_action_menu_surfaces}&owner={ADMIN_USER}",
        wait_until="load",
    )
    dashboard_page.page.wait_for_load_state("networkidle")
    return CustomDashboard(
        dashboard_page.page,
        page_title=_action_menu_dashboard_title(surface.title),
        navigate_to_page=False,
        # The average-scatterplot widget's mean/median computation over RRD data can push
        # the initial page render past the default expect timeout, see the docstring of
        # `fixture_dashboard_action_menu_surfaces` above.
        dashboard_name_timeout=(
            TIMEOUT_SLOW_DASHBOARD_LOAD_MS if surface.key == "scatterplot_widget" else None
        ),
    )
