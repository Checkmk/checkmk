#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""One consistent way to reach a graph regardless of which surface hosts it.

Resolves the container scoping a graph, absorbing surface-specific concerns
(dashboard-widget scoping, designer-preview container, iframe boundaries).
"""

import logging

from playwright.sync_api import Locator

from tests.system.gui.testlib.playwright.pom.graphing.graph_surfaces import GraphContainment
from tests.system.gui.testlib.playwright.pom.page import CmkPage

logger = logging.getLogger(__name__)

# Container of the legacy graph rendering. Uses the always-present ``div.graph`` rather
# than the ``div.graph_with_timeranges`` wrapper, which is absent on the forecast and
# dashboard-widget surfaces (show_time_range_previews defaults to False there).
_GRAPH_CONTAINER_SELECTOR = "div.graph:not(.preview)"
_DESIGNER_PREVIEW_SELECTOR = "#graph_0"

# The engine mounts one graph group per painter, holding a panel per graph it resolved.
ENGINE_GRAPH_GROUP_SELECTOR = ".graphing-graph-group"
ENGINE_GRAPH_PANEL_SELECTOR = ".graphing-graph-panel"
# The designer embeds a single panel of its own instead of a painter's group.
_ENGINE_DESIGNER_PREVIEW_SELECTOR = ".graphing-designer-body__preview"

# A dashboard widget hosts a single graph and none of the panel's chrome, so the engine
# mounts a figure there instead of a group of panels. Neither marker appears on the other's
# surface, which is why a widget needs its own accessor rather than `graph_root`.
_ENGINE_GRAPH_FIGURE_SELECTOR = ".graphing-graph-figure"


class GraphAccessor:
    """Resolve the container that hosts a graph, hiding surface differences.

    Reuses ``owner.main_area`` so the existing mixed-version iframe handling applies.
    """

    def __init__(self, owner: CmkPage) -> None:
        self._owner = owner
        self.page = owner.page

    def container(
        self,
        containment: GraphContainment,
        *,
        widget: Locator | None = None,
        iframed: bool = False,
    ) -> Locator:
        """Return the locator scoping the graph for the given containment context.

        ``widget`` is required for `DASHBOARD_WIDGET` (from e.g.
        ``BaseDashboard.get_widget``); ``iframed`` descends through the widget's iframe.
        """
        match containment:
            case GraphContainment.PAGE_DIRECT:
                return self._owner.main_area.locator(_GRAPH_CONTAINER_SELECTOR)
            case GraphContainment.DESIGNER_PREVIEW:
                return self._owner.main_area.locator(_DESIGNER_PREVIEW_SELECTOR)
            case GraphContainment.DASHBOARD_WIDGET:
                if widget is None:
                    raise ValueError(
                        "A widget locator is required for DASHBOARD_WIDGET containment."
                    )
                if iframed:
                    return widget.frame_locator("iframe").locator(_GRAPH_CONTAINER_SELECTOR)
                return widget.locator(_GRAPH_CONTAINER_SELECTOR)
            case _:
                raise ValueError(f"Unknown graph containment: {containment!r}")

    def engine_graph_group(
        self,
        containment: GraphContainment = GraphContainment.PAGE_DIRECT,
        *,
        widget: Locator | None = None,
        iframed: bool = False,
        within: Locator | None = None,
    ) -> Locator:
        """Return the engine's graph group scoping every graph of one painter.

        ``within`` narrows `PAGE_DIRECT` to one part of the page, for a surface that hosts
        several groups and needs the one belonging to a given slot.

        Only the surfaces driven by a painter have one. The designer embeds a single panel
        of its own, so reach for `graph_root` there instead.
        """
        match containment:
            case GraphContainment.PAGE_DIRECT:
                if within is not None:
                    return within.locator(ENGINE_GRAPH_GROUP_SELECTOR)
                return self._owner.main_area.locator(ENGINE_GRAPH_GROUP_SELECTOR)
            case GraphContainment.DASHBOARD_WIDGET:
                if widget is None:
                    raise ValueError(
                        "A widget locator is required for DASHBOARD_WIDGET containment."
                    )
                if iframed:
                    return widget.frame_locator("iframe").locator(ENGINE_GRAPH_GROUP_SELECTOR)
                return widget.locator(ENGINE_GRAPH_GROUP_SELECTOR)
            case _:
                raise ValueError(f"No painter graph group on containment: {containment!r}")

    def engine_graph_figure(
        self,
        containment: GraphContainment = GraphContainment.DASHBOARD_WIDGET,
        *,
        widget: Locator,
        iframed: bool = False,
    ) -> Locator:
        """Return the engine's figure holding the one graph a dashboard widget shows."""
        if containment is not GraphContainment.DASHBOARD_WIDGET:
            raise ValueError(f"The engine renders no figure on containment: {containment!r}")
        if iframed:
            return widget.frame_locator("iframe").locator(_ENGINE_GRAPH_FIGURE_SELECTOR)
        return widget.locator(_ENGINE_GRAPH_FIGURE_SELECTOR)

    def graph_root(
        self,
        containment: GraphContainment = GraphContainment.PAGE_DIRECT,
        *,
        widget: Locator | None = None,
        iframed: bool = False,
        within: Locator | None = None,
    ) -> Locator:
        """Return every graph the engine rendered on this surface.

        Matches multiple elements, so a single-element action raises Playwright
        strict-mode: anchor the count first with ``expect(loc).to_have_count(n)`` (which
        auto-waits for each graph to render, unlike ``.all()`` / ``.count()``), then
        address them via ``.nth(i)``.
        """
        if containment is GraphContainment.DESIGNER_PREVIEW:
            return self._owner.main_area.locator(_ENGINE_DESIGNER_PREVIEW_SELECTOR)
        return self.engine_graph_group(
            containment, widget=widget, iframed=iframed, within=within
        ).locator(ENGINE_GRAPH_PANEL_SELECTOR)
