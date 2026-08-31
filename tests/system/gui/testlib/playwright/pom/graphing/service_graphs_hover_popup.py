#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""The graph popup shown by hovering a service's graphs icon on a service list view."""

import logging

from playwright.sync_api import Locator

from tests.system.gui.testlib.playwright.pom.graphing.graph_accessor import GraphAccessor
from tests.system.gui.testlib.playwright.pom.graphing.graph_surfaces import GraphContainment
from tests.system.gui.testlib.playwright.pom.graphing.timeseries_graph import GraphPanel
from tests.system.gui.testlib.playwright.pom.monitor.services_of_host import ServicesOfHostPage

logger = logging.getLogger(__name__)

# The engine graph group mounts into this wrapper inside the hover menu (div#hover_menu),
# which the legacy hover module teleports onto <body>.
_HOVER_GRAPH_POPUP_SELECTOR = ".cmk_graph_hover"


class ServiceGraphsHoverPopup:
    """The graphs popup opened by hovering a service's graphs icon.

    The popup mounts graph panels with disabled interactions and legend, so only the title, the
    time information and the plot (canvas + axes) are shown. The popup is teleported to <body> and
    vanishes once the cursor leaves the icon.
    """

    def __init__(self, service_list: ServicesOfHostPage, host_name: str, service_name: str) -> None:
        self._service_list = service_list
        self._host_name = host_name
        self._service_name = service_name
        self.page = service_list.page
        self._accessor = GraphAccessor(service_list)

    @property
    def popup(self) -> Locator:
        """The wrapper the engine graph group mounts into."""
        return self._service_list.main_area.locator(_HOVER_GRAPH_POPUP_SELECTOR)

    @property
    def panels(self) -> Locator:
        """Every graph panel the engine rendered inside the popup."""
        return self._accessor.graph_root(GraphContainment.PAGE_DIRECT, within=self.popup)

    def panel(self, index: int = 0) -> GraphPanel:
        """A single graph panel retrieved via its index."""
        return GraphPanel(self.panels.nth(index), self.page, self._service_list.main_area)

    @property
    def broken_graphs(self) -> Locator:
        """The notices shown in place of graphs the popup could not load."""
        return self.popup.locator(".graphing-graph-notice--error")

    def open(self) -> ServiceGraphsHoverPopup:
        """Hover the graphs icon and wait for the popup's first plot to render.

        Returns self so callers can chain; the group assigns every graph in one tick, so the
        first plot appearing means the popup is ready.
        """
        icon = self._service_list.services_table.service_graphs_icon(
            self._host_name, self._service_name
        )
        logger.info("Hovering the graph icon of service '%s'", self._service_name)
        icon.hover()
        self.panel(0).graph.canvas.wait_for(state="visible")
        return self

    def close(self) -> None:
        """Move the pointer off the icon so the hover handler dismisses the popup."""
        self.page.mouse.move(0, 0)
