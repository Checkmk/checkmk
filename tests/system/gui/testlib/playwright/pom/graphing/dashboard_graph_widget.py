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

from tests.system.gui.testlib.playwright.pom.graphing.graph_accessor import GraphAccessor
from tests.system.gui.testlib.playwright.pom.graphing.graph_surfaces import GraphContainment
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

    def graph_container(self) -> Locator:
        """Return the container scoping the graph within the widget."""
        return self._accessor.container(
            GraphContainment.DASHBOARD_WIDGET, widget=self.widget, iframed=self._iframed
        )
