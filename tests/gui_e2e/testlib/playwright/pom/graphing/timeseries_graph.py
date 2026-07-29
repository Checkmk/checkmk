#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Page objects for the graph engine's rendered graphs and their canvas gestures."""

import logging

from playwright.sync_api import FloatRect, Locator, Page

from tests.gui_e2e.testlib.playwright.pom.graphing.graph_accessor import GraphAccessor
from tests.gui_e2e.testlib.playwright.pom.graphing.graph_surfaces import GraphContainment
from tests.gui_e2e.testlib.playwright.pom.monitor.service import ServicePage
from tests.gui_e2e.testlib.playwright.pom.page import MainArea

logger = logging.getLogger(__name__)

# The gestures listen on window mousemove, so a single jump from press to release never
# updates the preview.
_DRAG_STEPS = 12


def _point_in(box: FloatRect, x_fraction: float, y_fraction: float) -> tuple[float, float]:
    return box["x"] + box["width"] * x_fraction, box["y"] + box["height"] * y_fraction


def _drag(page: Page, start: tuple[float, float], end: tuple[float, float]) -> None:
    page.mouse.move(*start)
    page.mouse.down()
    for step in range(1, _DRAG_STEPS + 1):
        page.mouse.move(
            start[0] + (end[0] - start[0]) * step / _DRAG_STEPS,
            start[1] + (end[1] - start[1]) * step / _DRAG_STEPS,
        )
    page.mouse.up()


def _axis_label_texts(labels: Locator) -> list[str]:
    """Read axis tick labels.

    ``all_inner_texts`` is unusable here: ``innerText`` is an HTMLElement property and the
    labels are SVG ``<text>``, so it yields None per element. Stripped to match the
    whitespace normalisation `expect(...).to_have_text` applies to the same locator.
    """
    return [text.strip() for text in labels.all_text_contents()]


class TimeSeriesGraph:
    """One graph drawn by the engine: its canvas, axes and overlays.

    Args:
        root: the rendered graph component scoping every locator below.
        page: the page hosting it, needed to drive mouse gestures.
        document: the page's main area, for overlays that teleport out of `root`.
    """

    def __init__(self, root: Locator, page: Page, document: MainArea) -> None:
        self.root = root
        self.page = page
        self._document = document

    @property
    def canvas(self) -> Locator:
        """The plot the curves are drawn to.

        Pinned to the canvas rather than the role alone: the reset button's icon is an
        unnamed ``<img>``, so a bare role query matches it too once a zoom has been applied.
        Keeping ``role="img"`` in the selector still fails here if the plot loses it.
        """
        return self.root.locator("canvas[role='img']")

    @property
    def axis_grab_strip(self) -> Locator:
        """The transparent strip over the x-axis labels that arms a pan."""
        return self.root.locator(".graphing-time-series-graph__pan-zone")

    @property
    def reset_zoom_button(self) -> Locator:
        return self.root.get_by_role("button", name="Reset zoom")

    @property
    def add_pin_handle(self) -> Locator:
        """The handle the hover offers above the plot for pinning the hovered point."""
        return self.root.get_by_role("button", name="Add pin")

    @property
    def pin_handle(self) -> Locator:
        """The handle sitting on the pinned point; it is also the control that removes it."""
        return self.root.get_by_role("button", name="Remove pin")

    @property
    def tooltip(self) -> Locator:
        """The hover tooltip.

        Teleported to ``<body>`` rather than rendered inside the graph, so it is addressed
        from the document. It is also deliberately ``aria-hidden`` (pointer-only ephemera),
        so no role query reaches it.
        """
        return self._document.locator(".graphing-graph-tooltip")

    def tooltip_rows(self) -> list[tuple[str, str]]:
        """The hovered point's entries as (label, value) pairs."""
        rows = self._document.locator(".graphing-graph-tooltip__row")
        return [
            (
                row.locator(".graphing-graph-tooltip__label").inner_text().strip(),
                row.locator(".graphing-graph-tooltip__value").inner_text().strip(),
            )
            for row in rows.all()
        ]

    @property
    def time_axis_labels(self) -> Locator:
        """The x-axis tick labels; they change whenever the visible window moves.

        A locator rather than a list so assertions retry: the axes settle through a D3
        transition shortly after a gesture ends, not at once.
        """
        return self.root.locator(".graphing-time-series-graph__x-labels text")

    @property
    def value_axis_labels(self) -> Locator:
        """The y-axis tick labels; they change whenever the value domain moves."""
        return self.root.locator(".graphing-time-series-graph__y-axis text")

    def time_axis_label_texts(self) -> list[str]:
        return _axis_label_texts(self.time_axis_labels)

    def value_axis_label_texts(self) -> list[str]:
        return _axis_label_texts(self.value_axis_labels)

    def _canvas_box(self) -> FloatRect:
        box = self.canvas.bounding_box()
        assert box is not None, "The graph canvas has no layout box; is the graph rendered?"
        return box

    def drag_across_canvas(self, from_fraction: float, to_fraction: float) -> None:
        """Drag horizontally across the plot; in time-zoom mode this narrows the window."""
        box = self._canvas_box()
        logger.info("Dragging the canvas from %s to %s of its width", from_fraction, to_fraction)
        _drag(self.page, _point_in(box, from_fraction, 0.5), _point_in(box, to_fraction, 0.5))

    def drag_down_canvas(self, from_fraction: float, to_fraction: float) -> None:
        """Drag vertically down the plot; in peak-zoom mode this narrows the value domain."""
        box = self._canvas_box()
        logger.info("Dragging the canvas from %s to %s of its height", from_fraction, to_fraction)
        _drag(self.page, _point_in(box, 0.5, from_fraction), _point_in(box, 0.5, to_fraction))

    def drag_axis_strip(self, from_fraction: float, to_fraction: float) -> None:
        """Grab the x-axis strip and pull it sideways, panning the window."""
        box = self.axis_grab_strip.bounding_box()
        assert box is not None, "The x-axis grab strip has no layout box; is panning enabled?"
        logger.info("Panning the axis strip from %s to %s", from_fraction, to_fraction)
        _drag(self.page, _point_in(box, from_fraction, 0.5), _point_in(box, to_fraction, 0.5))

    def hover_canvas(self, x_fraction: float = 0.5, y_fraction: float = 0.5) -> None:
        box = self._canvas_box()
        self.page.mouse.move(*_point_in(box, x_fraction, y_fraction))

    def add_pin(self, x_fraction: float = 0.5) -> None:
        """Hover the plot and pin the point the hover resolved."""
        logger.info("Pinning the point at %s of the plot width", x_fraction)
        self.hover_canvas(x_fraction)
        self.add_pin_handle.click()

    def remove_pin(self) -> None:
        """Click the handle on the pinned point.

        Pinning the hovered point leaves the hover's own handle stacked on the pin's, so the
        pointer has to leave the plot and the hover lapse before the pin's handle is the one
        a click reaches.
        """
        self.root.hover(position={"x": 0, "y": 0})
        self.add_pin_handle.wait_for(state="detached")
        self.pin_handle.click()


class GraphPanel:
    """A graph plus the controls the panel wraps it in: header, context view, legend.

    Args:
        root: the panel scoping the graph and its controls.
        page: the page hosting it, needed to drive mouse gestures.
        document: the page's main area, forwarded to the graph.
    """

    def __init__(self, root: Locator, page: Page, document: MainArea) -> None:
        self.root = root
        self.page = page
        self.graph = TimeSeriesGraph(root.locator(".graphing-time-series-graph"), page, document)

    @property
    def header(self) -> Locator:
        return self.root.locator(".graphing-graph-header")

    @property
    def resolution_note(self) -> Locator:
        return self.root.locator(".graphing-graph-header__resolution")

    @property
    def peak_zoom_switch(self) -> Locator:
        """The Time zoom / Peak zoom switch that selects which axis a drag zooms."""
        return self.header.get_by_role("switch")

    @property
    def legend(self) -> Locator:
        return self.root.locator(".graphing-graph-legend")

    @property
    def context_view(self) -> Locator:
        """The brush strip below the plot (the context view)."""
        return self.root.locator(".graphing-graph-brush")

    @property
    def context_view_window(self) -> Locator:
        return self.context_view.locator(".graphing-graph-brush__window")

    @property
    def context_view_bar(self) -> Locator:
        """The drag bar under the context view's selection window."""
        return self.context_view.locator(".graphing-graph-brush__bar")

    def drag_context_view(self, offset_fraction: float) -> None:
        """Drag the context view's bar sideways by a fraction of the strip's width."""
        bar_box = self.context_view_bar.bounding_box()
        strip_box = self.context_view.bounding_box()
        assert bar_box is not None and strip_box is not None, (
            "The context view has no layout box; is it rendered?"
        )
        start = (bar_box["x"] + bar_box["width"] / 2, bar_box["y"] + bar_box["height"] / 2)
        end = (start[0] + strip_box["width"] * offset_fraction, start[1])
        logger.info("Dragging the context view by %s of the strip width", offset_fraction)
        _drag(self.page, start, end)

    def select_peak_zoom(self) -> None:
        if self.peak_zoom_switch.get_attribute("aria-checked") != "true":
            self.peak_zoom_switch.click()


class ServiceGraphs:
    """The engine's graph panels on the service detail page, plus the global time picker.

    Args:
        service_page: the service detail page-object hosting the graphs. It stays
            reachable as `owner` so tests can use its chrome (the user menu, for
            instance) without building a second page-object for the same tab.
    """

    def __init__(self, service_page: ServicePage) -> None:
        self.owner = service_page
        self.page = service_page.page
        self._main_area = service_page.main_area
        self._accessor = GraphAccessor(service_page)

    @property
    def panels(self) -> Locator:
        """Every graph the engine rendered, matched through the shared accessor."""
        return self._accessor.graph_root(GraphContainment.PAGE_DIRECT)

    def panel(self, index: int = 0) -> GraphPanel:
        return GraphPanel(self.panels.nth(index), self.page, self._main_area)

    def panel_count(self) -> int:
        # ``.count()`` does not auto-wait, so this is only correct once
        # ``wait_until_rendered`` has run. The group mounts every panel in one tick, so the
        # first panel being on screen means the rest are too.
        return self.panels.count()

    def all_panels(self) -> list[GraphPanel]:
        return [self.panel(index) for index in range(self.panel_count())]

    @property
    def global_time_picker(self) -> Locator:
        return self._main_area.locator(".graphing-global-time-picker")

    @property
    def active_preset_chip(self) -> Locator:
        """The highlighted time-range preset; empty once the window is a custom one."""
        return self.global_time_picker.locator('[aria-pressed="true"]')

    @property
    def refresh_indicator(self) -> Locator:
        """The live/paused refresh pill beside the time picker."""
        return self.global_time_picker.locator(".graphing-global-refresh-control")

    @property
    def resume_refresh_button(self) -> Locator:
        return self.refresh_indicator.get_by_role("button", name="Resume")

    def reload(self) -> None:
        """Reload the page and wait for the graphs to come back."""
        logger.info("Reloading the page holding the graphs")
        self.page.reload()
        self.wait_until_rendered()

    def wait_until_rendered(self) -> None:
        """Wait for the graphs to be on screen.

        The first panel is enough: the group assigns all of its graphs in one go once every
        fetch has resolved, so the panels appear together rather than trickling in.
        """
        self.panel(0).graph.canvas.wait_for(state="visible")
