#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Accessor for graphs embedded as dashboard widgets.

Covers every dashboard graph widget (template/combined/custom/single-timeseries/
problem-percentage, scatterplot, alert & notifications): locates the widget via an
existing dashboard page-object, then defers to the shared `GraphAccessor`.
"""

import logging

from playwright.sync_api import Locator

from tests.system.gui.testlib.playwright.pom.graphing.graph_accessor import (
    ACTION_MENU_BUTTON_NAME,
    ACTION_MENU_DROPDOWN_SELECTOR,
    GraphAccessor,
)
from tests.system.gui.testlib.playwright.pom.graphing.graph_surfaces import GraphContainment
from tests.system.gui.testlib.playwright.pom.graphing.timeseries_graph import TimeSeriesGraph
from tests.system.gui.testlib.playwright.pom.monitor.dashboard import BaseDashboard

logger = logging.getLogger(__name__)


class DashboardGraphWidget:
    """A graph rendered inside a dashboard widget.

    Args:
        dashboard: the dashboard page-object hosting the widget.
        widget_title: the title of the graph widget on the dashboard.
        iframed: whether the widget renders its content inside an iframe.
    """

    def __init__(
        self, dashboard: BaseDashboard, widget_title: str, *, iframed: bool = False
    ) -> None:
        self._dashboard = dashboard
        self.widget_title = widget_title
        self._iframed = iframed
        self._accessor = GraphAccessor(dashboard)

    @property
    def widget(self) -> Locator:
        return self._dashboard.get_widget(self.widget_title)

    @property
    def figure(self) -> Locator:
        """The engine's figure inside the widget."""
        return self._accessor.engine_graph_figure(
            GraphContainment.DASHBOARD_WIDGET, widget=self.widget, iframed=self._iframed
        )

    @property
    def graph(self) -> TimeSeriesGraph:
        """The graph the figure draws, with the same canvas and axes as on any other surface."""
        return TimeSeriesGraph(
            self.figure.locator(".graphing-time-series-graph"),
            self._dashboard.page,
            self._dashboard.main_area,
        )

    @property
    def notice(self) -> Locator:
        """The notice the figure shows in place of the graph it could not load.

        A sibling of the graph rather than a branch beside it, so it is also what a failed
        refetch states over data that is still on screen.
        """
        return self.figure.locator(".graphing-graph-figure__notice")

    def wait_until_rendered(self) -> None:
        """Wait for the graph to be on screen.

        The widget holds a single graph, so its canvas being visible is the whole surface
        having rendered.
        """
        self.graph.canvas.wait_for(state="visible")

    def action_menu_button(self) -> Locator:
        """Return the widget's action-menu (burger menu) trigger button, if any."""
        return self.widget.get_by_role("button", name=ACTION_MENU_BUTTON_NAME, exact=True)

    def open_action_menu(self) -> Locator:
        """Open the action menu and return the locator of its dropdown."""
        self.action_menu_button().click()
        return self.widget.locator(ACTION_MENU_DROPDOWN_SELECTOR)
