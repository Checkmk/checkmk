#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Graph loading and error states.

The single test here is the browser backstop for the whole concern: it proves the
skeleton -> canvas transition wires up against a real fetch. Everything else - the fast
load, the widgets' spinner and its containment, the error states and their retry - is
component-level behaviour and is covered in the Vitest suites (`GraphGroup.test.ts`,
`DashboardContentGraph.test.ts`), where the pending, 500 and 404 responses can be driven
exactly.

The remaining surfaces need no browser test of their own: each renders the same
`cmk-graph-group`, so the skeleton follows from `GraphGroup`.
"""

from playwright.sync_api import expect, Route

from tests.system.gui.testlib.playwright.pom.graphing.fixtures import SERVICE_WITH_GRAPHS
from tests.system.gui.testlib.playwright.pom.graphing.timeseries_graph import ServiceGraphs
from tests.system.gui.testlib.playwright.pom.monitor.dashboard import MainDashboard
from tests.system.gui.testlib.playwright.pom.monitor.service import ServicePage
from tests.system.gui.testlib.playwright.pom.monitor.services_of_host import ServicesOfHostPage

# The endpoint every rendered graph fetches its data from; holding it holds the load window open.
_GRAPH_DATA_URL = "**/domain-types/graph/actions/fetch_data/invoke"


def _open_service_graphs(dashboard_page: MainDashboard, host_name: str) -> ServiceGraphs:
    """Navigate to the service detail page without waiting for its graphs to render."""
    services_of_host = ServicesOfHostPage(dashboard_page.page, host_name=host_name)
    services_of_host.services_table.host_services_table(host_name).get_by_role(
        "link", name=SERVICE_WITH_GRAPHS, exact=True
    ).click()
    return ServiceGraphs(
        ServicePage(
            dashboard_page.page,
            host_name=host_name,
            service_name=SERVICE_WITH_GRAPHS,
            navigate_to_page=False,
        )
    )


def test_skeleton_visible_while_loading_then_canvas(
    dashboard_page: MainDashboard,
    graph_hosts_with_varying_data: list[str],
    javascript_errors: list[str],
) -> None:
    """A page skeleton shows during load, then the canvas.

    The requests are collected and continued by hand rather than delayed inside the handler:
    the sync API runs handlers on the thread the assertions need, so a sleeping handler would
    hold the assertions back exactly as long as it holds the response.

    The handler stops holding rather than being unrouted: `unroute` cancels the invocations
    still pending in it, which marks their routes handled and leaves nothing left to continue.
    """
    held: list[Route] = []
    holding = True

    def hold(route: Route) -> None:
        # A refresh landing after the release must not be held, or it would pend to teardown.
        if holding:
            held.append(route)
        else:
            route.continue_()

    dashboard_page.page.route(_GRAPH_DATA_URL, hold)

    graphs = _open_service_graphs(dashboard_page, graph_hosts_with_varying_data[0])

    expect(
        graphs.skeletons.first,
        "No skeleton stood in for the panels while the graph data was still pending",
    ).to_be_visible()

    assert held, "The page never requested its graph data, so nothing was ever held"
    holding = False
    for route in held:
        route.continue_()

    graphs.wait_until_rendered()
    expect(
        graphs.skeletons,
        "The skeleton outlived the data it was standing in for",
    ).to_have_count(0)
    assert not javascript_errors, f"The load raised uncaught page errors: {javascript_errors}"
