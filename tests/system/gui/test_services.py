#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import time

import pytest
from faker import Faker
from playwright.sync_api import expect

from tests.system.gui.testlib.api_helpers import LOCALHOST_IPV4
from tests.system.gui.testlib.host_details import AgentAndApiIntegration, HostDetails, SNMP
from tests.system.gui.testlib.playwright.pom.graphing.graph_accessor import GraphAccessor
from tests.system.gui.testlib.playwright.pom.graphing.graph_surfaces import GraphContainment
from tests.system.gui.testlib.playwright.pom.graphing.service_graphs_hover_popup import (
    ServiceGraphsHoverPopup,
)
from tests.system.gui.testlib.playwright.pom.graphing.timeseries_graph import ServiceGraphs
from tests.system.gui.testlib.playwright.pom.monitor.combined_graph import (
    CombinedGraphsServiceSearch,
)
from tests.system.gui.testlib.playwright.pom.monitor.dashboard import MainDashboard
from tests.system.gui.testlib.playwright.pom.monitor.service_search import ServiceSearchPage

logger = logging.getLogger(__name__)

# A graph that rendered must have asked this: the page ships no series data of its own.
_ENGINE_GRAPH_ENDPOINT = "domain-types/graph/actions/fetch_data/invoke"


@pytest.mark.parametrize(
    "created_host",
    [
        pytest.param(
            HostDetails(
                name=f"test_host_{Faker().first_name()}",
                ip=LOCALHOST_IPV4,
                agent_and_api_integration=AgentAndApiIntegration.no_agent,
                snmp=SNMP.no_snmp,
            )
        )
    ],
    indirect=["created_host"],
)
def test_reschedule_active_checks(dashboard_page: MainDashboard, created_host: HostDetails) -> None:
    """Test reschedule active checks.

    Create a host with a 'PING' service. Navigate to 'Service search' page and reschedule active
    checks. Check that the 'age' of the 'PING' service is updated.
    """
    host_name = created_host.name
    service_search_page = ServiceSearchPage(dashboard_page.page)

    logger.info("Apply filters and wait for the table to load")
    service_search_page.filter_sidebar.apply_host_filter(host_name)
    service_search_page.filter_sidebar.apply_filters(service_search_page.services_table)

    sleep_time = 5
    logger.info("Offset 'checked' state to at least %s seconds for test validation", sleep_time)
    time.sleep(sleep_time)

    logger.info("Reschedule active checks")
    service_search_page.main_area.click_item_in_dropdown_list(
        "Commands", "Reschedule active checks"
    )
    expect(service_search_page.reschedule_active_checks_popup).to_be_visible()
    service_search_page.spread_over_minutes_textbox.fill("0")
    service_search_page.reschedule_button.click()
    expect(service_search_page.reschedule_active_checks_confirmation_window).to_be_visible()
    service_search_page.reschedule_button.click()

    logger.info("Navigate back to the Service search view")
    service_search_page.back_to_view_link.click()
    expect(service_search_page.services_table).to_be_visible()

    logger.info("Check that the service was rescheduled")
    services_count = service_search_page.service_rows(host_name).count()
    assert services_count == 1, "Unexpected number of services in the table"
    time_since_last_check = service_search_page.checked_column_cells(host_name).all_inner_texts()
    (number, unit) = time_since_last_check[0].split()
    assert unit == "ms" or (unit == "s" and float(number) < sleep_time), (
        "Service was not rescheduled"
    )


# Substrings: the engine renders the graph plug-in's own title, which carries neither the
# unique host/service nor the presentation.
@pytest.mark.parametrize(
    "service_filter, expected_graphs",
    [
        pytest.param(
            "cpu",
            ["CPU load", "CPU utilization"],
            id="cpu_service_filter",
        ),
        pytest.param(
            "filesystem",
            ["Used inodes", "Size and used space"],
            id="filesystem_service_filter",
        ),
    ],
)
def test_filtered_services_combined_graphs(
    dashboard_page: MainDashboard,
    service_filter: str,
    expected_graphs: list[str],
    linux_hosts: list[str],
) -> None:
    """Test filtered services combined graphs.

    Navigate to 'Service search' page, apply a filter, click on
    'All metrics of same type in one graph' and check that all expected graphs are displayed.
    """
    host_name = linux_hosts[0]
    service_search_page = ServiceSearchPage(dashboard_page.page)
    service_search_page.filter_sidebar.apply_host_filter(host_name)
    service_search_page.filter_sidebar.apply_service_filter(service_filter)
    service_search_page.filter_sidebar.apply_filters(service_search_page.services_table)
    service_search_page.main_area.click_item_in_dropdown_list(
        "Services", "All metrics of same type in one graph"
    )
    combined_graphs_service_search_page = CombinedGraphsServiceSearch(
        service_search_page.page, navigate_to_page=False
    )
    expect(combined_graphs_service_search_page.global_time_picker).to_be_visible()
    for graph_title in expected_graphs:
        logger.info("Check that the '%s' graph is displayed correctly", graph_title)
        combined_graphs_service_search_page.check_graph(graph_title)


def test_no_errors_on_combined_graphs_page(
    dashboard_page: MainDashboard, linux_hosts: list[str]
) -> None:
    """Test that there are no errors on the 'Combined graphs - Service search' page."""
    service_search_page = ServiceSearchPage(dashboard_page.page)
    service_search_page.filter_sidebar.apply_last_service_state_change_filter(
        "days ago", "1", "days ago", "0"
    )
    service_search_page.filter_sidebar.apply_filters(service_search_page.services_table)
    service_search_page.main_area.click_item_in_dropdown_list(
        "Services", "All metrics of same type in one graph"
    )
    combined_graphs_service_search_page = CombinedGraphsServiceSearch(
        service_search_page.page, navigate_to_page=False
    )
    combined_graphs_service_search_page.check_no_errors()
    # TODO: uncomment this after fixing CMK-19580
    # broken_graphs_count = combined_graphs_service_search_page.broken_graph.count()
    # assert (
    #    broken_graphs_count == 0
    # ), "There are broken graphs on the 'Combined graphs - Service search' page"


def test_service_graphs_render_through_the_engine(
    service_graphs: ServiceGraphs,
    javascript_errors: list[str],
    requested_urls: list[str],
) -> None:
    """The service detail page renders its graphs through the engine."""
    expect(
        service_graphs.panels, "The engine rendered no graph at all on the service detail page"
    ).not_to_have_count(0)
    # A drawn frame proves nothing on its own; the series have to have been fetched too.
    assert any(_ENGINE_GRAPH_ENDPOINT in url for url in requested_urls), (
        f"No graph data was fetched at all, so nothing here observed a graph being "
        f"rendered: {requested_urls}"
    )
    assert not javascript_errors, f"Rendering the graphs raised page errors: {javascript_errors}"


def test_service_graphs_have_titles_and_legend_not_broken(
    service_graphs: ServiceGraphs, javascript_errors: list[str]
) -> None:
    """Each service graph has a title and a legend, and none reports a failed load.

    Both the title and the legend rows are filled from the fetch response, so a graph
    showing either of them empty has drawn its frame without the data behind it.
    """
    expect(
        service_graphs.panels, "The engine rendered no graph at all on the service detail page"
    ).not_to_have_count(0)

    for index, panel in enumerate(service_graphs.all_panels()):
        expect(panel.title, f"Graph {index} rendered without a title").to_be_visible()
        expect(panel.title, f"Graph {index} rendered an empty title").not_to_have_text("")
        expect(panel.legend, f"Graph {index} rendered without a legend").to_be_visible()
        expect(
            panel.legend.locator(".graphing-graph-legend__row"),
            f"The legend of graph {index} lists no metric",
        ).not_to_have_count(0)

    expect(
        service_graphs.broken_graphs,
        "A graph reported that it could not be loaded",
    ).to_have_count(0)
    assert not javascript_errors, f"Rendering the graphs raised page errors: {javascript_errors}"


def test_combined_graphs_render_through_the_engine(
    combined_graphs_page: CombinedGraphsServiceSearch,
    javascript_errors: list[str],
    requested_urls: list[str],
) -> None:
    """Every card of the combined-graphs page is rendered by the engine.

    Each card is checked for its own plot rather than for an engine element of its own: the
    page mounts a single component holding all of them, so only the per-card plot separates
    "the engine drew every card" from "it drew the first one".
    """
    expect(
        combined_graphs_page.panels, "The engine rendered no graph card at all"
    ).not_to_have_count(0)
    expect(
        GraphAccessor(combined_graphs_page).engine_graph_group(GraphContainment.PAGE_DIRECT),
        "The page did not mount exactly one engine component to hold its cards",
    ).to_have_count(1)
    for index, panel in enumerate(combined_graphs_page.all_panels()):
        expect(panel.graph.canvas, f"Graph card {index} rendered no plot").to_be_visible()
    # A drawn frame proves nothing on its own; the series have to have been fetched too.
    assert any(_ENGINE_GRAPH_ENDPOINT in url for url in requested_urls), (
        f"No graph data was fetched at all, so nothing here observed a card being "
        f"rendered: {requested_urls}"
    )
    assert not javascript_errors, f"Rendering the graphs raised page errors: {javascript_errors}"


def test_combined_graphs_have_no_broken_graphs(
    combined_graphs_page: CombinedGraphsServiceSearch, javascript_errors: list[str]
) -> None:
    """No card of the combined-graphs page reports a failed load.

    The cards stack well past the viewport, so each is scrolled to before the page is
    judged. The notices land in the DOM either way, but only a card that was actually
    painted can raise an error while painting.
    """
    expect(
        combined_graphs_page.panels, "The engine rendered no graph card at all"
    ).not_to_have_count(0)

    for panel in combined_graphs_page.all_panels():
        panel.graph.canvas.scroll_into_view_if_needed()

    expect(
        combined_graphs_page.broken_graph, "A graph card reported that it could not be loaded"
    ).to_have_count(0)
    assert not javascript_errors, f"Rendering the graphs raised page errors: {javascript_errors}"


def test_combined_graphs_over_all_services_have_no_broken_graphs(
    combined_graphs_page_all_services: CombinedGraphsServiceSearch,
    javascript_errors: list[str],
) -> None:
    """A card gathering several of a host's services loads, as one over a single service does.

    This is the page a user reaches from a host's service list, and the only one of the two
    where the engine has to combine anything: a card over one service exercises no
    combination at all.
    """
    combined_graphs = combined_graphs_page_all_services

    # The page settles on either cards or a notice. Waiting for whichever comes first is what
    # earns the two assertions below: without it, a page still rendering would satisfy both.
    expect(
        combined_graphs.panels.or_(combined_graphs.broken_graph).first,
        "The page rendered neither a graph card nor a notice explaining their absence",
    ).to_be_visible()

    expect(
        combined_graphs.broken_graph, "A graph card reported that it could not be loaded"
    ).to_have_count(0)
    expect(combined_graphs.panels, "The engine rendered no graph card at all").not_to_have_count(0)
    assert not javascript_errors, f"Rendering the graphs raised page errors: {javascript_errors}"


def test_graph_hover_preview_renders_its_expected_elements(
    service_graphs_hover_popup: ServiceGraphsHoverPopup,
    javascript_errors: list[str],
) -> None:
    """Upon hovering a service graphs icon on the "Services of host" view, a preview popup is
    rendered showing the service's graphs. The rendering includes the graph title, time information
    and plot (canvas + axes).
    """
    panel = service_graphs_hover_popup.open().panel(0)

    expect(panel.title, "The hover popup rendered a graph without a title").to_be_visible()
    expect(panel.title, "The hover popup rendered an empty graph title").not_to_have_text("")
    expect(panel.timestamp, "The hover popup rendered no time information").to_be_visible()
    expect(panel.graph.canvas, "The hover popup rendered no plot").to_be_visible()
    expect(
        panel.graph.time_axis_labels, "The hover popup's plot drew no time axis"
    ).not_to_have_count(0)
    expect(
        panel.graph.value_axis_labels, "The hover popup's plot drew no value axis"
    ).not_to_have_count(0)
    expect(
        service_graphs_hover_popup.broken_graphs, "A graph in the hover popup failed to load"
    ).to_have_count(0)

    service_graphs_hover_popup.close()
    expect(
        service_graphs_hover_popup.popup,
        "The hover popup stayed open after the pointer left the icon",
    ).to_be_hidden()

    assert not javascript_errors, f"The hover popup raised page errors: {javascript_errors}"
