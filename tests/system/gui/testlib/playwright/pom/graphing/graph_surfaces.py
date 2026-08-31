#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Registry of the graph surfaces the E2E suites target.

Captures every in-scope surface in one place so cross-surface tests can iterate
them instead of hard-coding their own list.
"""

from dataclasses import dataclass
from enum import StrEnum
from typing import Final

from tests.testlib.version import TypeCMKEdition


class GraphContainment(StrEnum):
    """How a graph is embedded on its surface (used by `GraphAccessor`)."""

    PAGE_DIRECT = "page_direct"
    DASHBOARD_WIDGET = "dashboard_widget"
    DESIGNER_PREVIEW = "designer_preview"


@dataclass(frozen=True, kw_only=True)
class GraphSurface:
    """A single graph surface and the metadata cross-surface tests iterate over."""

    key: str
    title: str
    containment: GraphContainment
    requires_pro: bool  # lives in the non-free "pro" component (not in community)
    # "module:ClassName" pointer to the navigation page-object (string, so the
    # registry stays decoupled from page-objects whose constructors need args).
    page_object: str
    notes: str = ""

    def available_in(self, edition: TypeCMKEdition) -> bool:
        return not (self.requires_pro and edition.is_community_edition())


GRAPH_SURFACES: Final[tuple[GraphSurface, ...]] = (
    GraphSurface(
        key="service_detail_graph",
        title="Service detail graph",
        containment=GraphContainment.PAGE_DIRECT,
        requires_pro=False,
        page_object="tests.system.gui.testlib.playwright.pom.monitor.service:ServicePage",
        notes="Template graphs rendered on the service detail page.",
    ),
    GraphSurface(
        key="combined_graphs",
        title="Combined graphs - Service search",
        containment=GraphContainment.PAGE_DIRECT,
        requires_pro=True,
        page_object=(
            "tests.system.gui.testlib.playwright.pom.monitor.combined_graph"
            ":CombinedGraphsServiceSearch"
        ),
        notes="Reached from the 'Service search' page; navigation depends on the applied filters.",
    ),
    GraphSurface(
        key="custom_graph",
        title="Custom graph",
        containment=GraphContainment.DESIGNER_PREVIEW,
        requires_pro=True,
        page_object=(
            "tests.system.gui.testlib.playwright.pom.graphing.custom_graph_designer"
            ":CustomGraphDesigner"
        ),
        notes="A saved custom graph shown in the designer's view mode.",
    ),
    GraphSurface(
        key="custom_graph_designer_preview",
        title="Custom graph designer preview",
        containment=GraphContainment.DESIGNER_PREVIEW,
        requires_pro=True,
        page_object=(
            "tests.system.gui.testlib.playwright.pom.graphing.custom_graph_designer"
            ":CustomGraphDesigner"
        ),
        notes="Graph preview rendered inside the designer while editing metric definitions.",
    ),
    GraphSurface(
        key="single_timeseries_widget",
        title="Single-timeseries widget",
        containment=GraphContainment.DASHBOARD_WIDGET,
        requires_pro=True,
        page_object=(
            "tests.system.gui.testlib.playwright.pom.graphing.dashboard_graph_widget"
            ":DashboardGraphWidget"
        ),
        notes="Single-timeseries graph widget (its own graphing-engine type).",
    ),
    GraphSurface(
        key="problem_percentage_widget",
        title="Problem-percentage widget",
        containment=GraphContainment.DASHBOARD_WIDGET,
        requires_pro=True,
        page_object=(
            "tests.system.gui.testlib.playwright.pom.graphing.dashboard_graph_widget"
            ":DashboardGraphWidget"
        ),
        notes="Problem-percentage graph widget (its own graphing-engine type).",
    ),
    GraphSurface(
        key="graph_collection",
        title="Graph collection",
        containment=GraphContainment.PAGE_DIRECT,
        requires_pro=True,
        page_object="tests.system.gui.testlib.playwright.pom.graphing.graph_collection:GraphCollection",
        notes="A container of other graphs; not itself a graphing-engine graph type.",
    ),
    GraphSurface(
        key="forecast_graph",
        title="Forecast graph",
        containment=GraphContainment.PAGE_DIRECT,
        requires_pro=True,
        page_object="tests.system.gui.testlib.playwright.pom.graphing.forecast_graph:ForecastGraph",
    ),
    GraphSurface(
        key="scatterplot_widget",
        title="Average scatterplot widget",
        containment=GraphContainment.DASHBOARD_WIDGET,
        requires_pro=True,
        page_object=(
            "tests.system.gui.testlib.playwright.pom.graphing.dashboard_graph_widget"
            ":DashboardGraphWidget"
        ),
        notes="Average scatterplot widget; drawn by the engine's time-series component.",
    ),
    GraphSurface(
        key="alert_notification_widget",
        title="Alert & notifications widget",
        containment=GraphContainment.DASHBOARD_WIDGET,
        requires_pro=True,
        page_object=(
            "tests.system.gui.testlib.playwright.pom.graphing.dashboard_graph_widget"
            ":DashboardGraphWidget"
        ),
        notes="Alert/notification bar-chart widget; also unified under the new engine.",
    ),
    GraphSurface(
        key="dashboard_graph_widget",
        title="Dashboard graph widget",
        containment=GraphContainment.DASHBOARD_WIDGET,
        requires_pro=False,
        page_object=(
            "tests.system.gui.testlib.playwright.pom.graphing.dashboard_graph_widget"
            ":DashboardGraphWidget"
        ),
        notes="Template/combined/custom graph widgets embedded in a dashboard.",
    ),
    GraphSurface(
        key="service_graphs_hover_popup",
        title="Service graphs hover popup",
        containment=GraphContainment.PAGE_DIRECT,
        requires_pro=False,
        page_object=(
            "tests.system.gui.testlib.playwright.pom.graphing.service_graphs_hover_popup"
            ":ServiceGraphsHoverPopup"
        ),
        notes="Popup containing service graphs opened when the service's graphs icon is hovered",
    ),
)


def surfaces_for_edition(edition: TypeCMKEdition) -> tuple[GraphSurface, ...]:
    """Return the graph surfaces reachable in the given (running site) edition."""
    return tuple(surface for surface in GRAPH_SURFACES if surface.available_in(edition))


SURFACES_BY_KEY: Final[dict[str, GraphSurface]] = {
    surface.key: surface for surface in GRAPH_SURFACES
}
