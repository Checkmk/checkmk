#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Canvas interactions of the graph engine, on the service detail page"""

import logging

import pytest
from playwright.sync_api import expect

from tests.system.gui.testlib.playwright.pom.graphing.fixtures import (
    open_service_graphs,
    UserGraphPin,
)
from tests.system.gui.testlib.playwright.pom.graphing.timeseries_graph import ServiceGraphs
from tests.system.gui.testlib.playwright.pom.monitor.dashboard import MainDashboard
from tests.testlib.common.utils import wait_until

logger = logging.getLogger(__name__)

_VALUE_AXIS_RESCALE_TIMEOUT = 10

# Two pixels of a plot a thousand wide: each handle sits on a whole pixel of its own plot.
_PIN_ALIGNMENT_TOLERANCE = 0.002


def _mark_document(graphs: ServiceGraphs) -> None:
    """Tag the document so a full page reload is detectable by the tag's absence."""
    graphs.page.evaluate("window.__cmkGraphInteractionMarker = true")


def _document_survived(graphs: ServiceGraphs) -> bool:
    return bool(graphs.page.evaluate("window.__cmkGraphInteractionMarker === true"))


def test_x_drag_zooms_every_graph_and_reset_returns(
    service_graphs: ServiceGraphs, javascript_errors: list[str]
) -> None:
    """Dragging across the plot narrows the time window on every graph, and resets.

    The drag is committed to the page's shared time range, so sibling graphs and the time
    picker follow it, and the reset control puts them all back.
    """
    panels = service_graphs.all_panels()
    windows_before = [panel.graph.time_axis_label_texts() for panel in panels]
    preset_before = service_graphs.active_preset_chip.inner_text()
    _mark_document(service_graphs)

    panels[0].graph.drag_across_canvas(0.3, 0.7)

    expect(
        panels[0].graph.reset_zoom_button,
        "Zooming did not offer a way back to the original window",
    ).to_be_visible()
    for panel, window_before in zip(panels, windows_before):
        expect(
            panel.graph.time_axis_labels,
            "A graph rendered no time axis labels at all",
        ).not_to_have_count(0)
        expect(
            panel.graph.time_axis_labels,
            "A graph kept its original window although the page's time range was narrowed",
        ).not_to_have_text(window_before)
    expect(
        service_graphs.active_preset_chip,
        "The picker still highlights a preset although the window is now a custom one",
    ).to_have_count(0)
    assert _document_survived(service_graphs), "Zooming reloaded the page instead of redrawing"

    panels[0].graph.reset_zoom_button.click()

    for panel, window_before in zip(panels, windows_before):
        expect(
            panel.graph.time_axis_labels,
            "A graph did not return to its pre-zoom window",
        ).to_have_text(window_before)
    expect(
        service_graphs.active_preset_chip,
        "The picker did not return to the preset it started on",
    ).to_have_text(preset_before)
    assert not javascript_errors, f"Uncaught JS errors during the zoom: {javascript_errors}"


def test_peak_zoom_narrows_the_value_axis_only(
    service_graphs: ServiceGraphs, javascript_errors: list[str]
) -> None:
    """A peak-zoom drag narrows the value axis and leaves the time axis alone.

    Locality across sibling graphs is covered by composables/zoomSync.test.ts; here the
    point is that the gesture reaches the value axis and stops there.

    A narrow band, not the middle half: outward tick alignment rounds a shallow zoom away.
    """
    panel = service_graphs.panel(0)
    panel.select_peak_zoom()
    time_before = panel.graph.time_axis_label_texts()
    ticks_before = panel.graph.value_axis_ticks()

    panel.graph.drag_down_canvas(0.4, 0.6)

    expect(
        panel.graph.value_axis_labels, "The graph rendered no value axis labels at all"
    ).not_to_have_count(0)
    wait_until(
        lambda: panel.graph.value_axis_ticks() != ticks_before,
        timeout=_VALUE_AXIS_RESCALE_TIMEOUT,
        condition_name="the peak-zoom drag to move the value axis",
    )
    expect(
        panel.graph.time_axis_labels,
        "A peak zoom moved the time axis, which belongs to the time zoom",
    ).to_have_text(time_before)
    assert not javascript_errors, f"Uncaught JS errors during the peak zoom: {javascript_errors}"


def test_axis_strip_drag_pans_every_graph(
    service_graphs: ServiceGraphs, javascript_errors: list[str]
) -> None:
    """Dragging the x-axis strip pans the window, and every graph on the page follows.

    The strip over the axis labels is the pan affordance, and the gesture is committed to
    the page's shared time range, so sibling graphs move with it.
    """
    panels = service_graphs.all_panels()
    windows_before = [panel.graph.time_axis_label_texts() for panel in panels]
    _mark_document(service_graphs)

    panels[0].graph.drag_axis_strip(0.6, 0.3)

    for panel, window_before in zip(panels, windows_before):
        expect(
            panel.graph.time_axis_labels,
            "A graph rendered no time axis labels at all",
        ).not_to_have_count(0)
        expect(
            panel.graph.time_axis_labels,
            "A graph kept its window although the page was panned",
        ).not_to_have_text(window_before)
    assert _document_survived(service_graphs), "Panning reloaded the page instead of redrawing"
    assert not javascript_errors, f"Uncaught JS errors during the pan: {javascript_errors}"


def test_context_view_drag_shifts_the_window(
    service_graphs: ServiceGraphs, javascript_errors: list[str]
) -> None:
    """Dragging the context view shifts the window without resizing it.

    Measured over the second drag: the page opens on a window ending at the newest sample,
    which the data source serves as-is, while every window behind it is served a step wider.
    Only drags that start away from the present are comparable.
    """
    panel = service_graphs.panel(0)
    expect(panel.context_view, "The service detail page has no context view").to_be_visible()
    window_before = panel.graph.time_axis_label_texts()

    panel.drag_context_view(-0.15)

    expect(
        panel.graph.time_axis_labels,
        "The graph rendered no time axis labels at all",
    ).not_to_have_count(0)
    expect(
        panel.graph.time_axis_labels,
        "Dragging the context view did not move the graph's window",
    ).not_to_have_text(window_before)
    service_graphs.wait_until_settled()
    bar_before = panel.context_view_bar.bounding_box()
    strip_before = panel.context_view.bounding_box()
    assert bar_before is not None and strip_before is not None

    panel.drag_context_view(-0.10)

    service_graphs.wait_until_settled()
    bar_after = panel.context_view_bar.bounding_box()
    strip_after = panel.context_view.bounding_box()
    assert bar_after is not None and strip_after is not None
    assert bar_after["width"] == pytest.approx(bar_before["width"], abs=2), (
        "Moving the context view resized its window instead of shifting it"
    )
    assert strip_after["width"] == pytest.approx(strip_before["width"], abs=2), (
        "Moving the context view changed the span of the overview strip"
    )
    assert not javascript_errors, f"Uncaught JS errors during the brush drag: {javascript_errors}"


def test_pinning_a_point_marks_it_on_every_graph_and_stores_it(
    dashboard_page: MainDashboard,
    graph_hosts_with_varying_data: list[str],
    admin_graph_pin: UserGraphPin,
    javascript_errors: list[str],
) -> None:
    """Pinning a point on one graph marks the same instant on every graph and reaches the site.

    Each value axis is as wide as its own labels, so the plots start at different x and the
    handles are compared as a fraction of their plot, not by page x.
    """
    graphs = open_service_graphs(dashboard_page.page, graph_hosts_with_varying_data[0])
    panel_count = graphs.panel_count()

    graphs.panel(0).graph.add_pin(0.4)

    expect(
        graphs.pin_handles, "A graph shows no pin although a point was pinned on the page"
    ).to_have_count(panel_count)
    graphs.wait_until_settled()
    positions = graphs.pin_positions()
    assert len(positions) == panel_count, f"A graph lost its pin while being measured: {positions}"
    assert max(positions) - min(positions) <= _PIN_ALIGNMENT_TOLERANCE, (
        f"The graphs pin different points of their window: {positions}"
    )
    assert admin_graph_pin.read() is not None, (
        "The site holds no pin although one was set on the page"
    )
    assert not javascript_errors, f"Uncaught JS errors while pinning: {javascript_errors}"


@pytest.mark.usefixtures("stored_graph_pin")
def test_a_stored_pin_marks_every_graph_when_the_page_opens(
    dashboard_page: MainDashboard,
    graph_hosts_with_varying_data: list[str],
    javascript_errors: list[str],
) -> None:
    """A pin the site stores for the user is on every graph as soon as the page opens."""
    host_name = graph_hosts_with_varying_data[0]

    graphs = open_service_graphs(dashboard_page.page, host_name)

    expect(
        graphs.pin_handles, "A graph opened without the pin the site stores for the user"
    ).to_have_count(graphs.panel_count())
    assert not javascript_errors, f"Uncaught JS errors showing the stored pin: {javascript_errors}"


@pytest.mark.usefixtures("stored_graph_pin")
def test_removing_the_pin_clears_every_graph_and_the_site(
    dashboard_page: MainDashboard,
    graph_hosts_with_varying_data: list[str],
    admin_graph_pin: UserGraphPin,
    javascript_errors: list[str],
) -> None:
    """Removing the pin on one graph takes it off every graph and off the site."""
    graphs = open_service_graphs(dashboard_page.page, graph_hosts_with_varying_data[0])

    graphs.panel(0).graph.remove_pin()

    expect(
        graphs.pin_handles, "A graph kept its pin although the pin was removed on the page"
    ).to_have_count(0)
    assert admin_graph_pin.read() is None, (
        "The site kept the pin although it was removed on the page"
    )
    assert not javascript_errors, f"Uncaught JS errors removing the pin: {javascript_errors}"


def test_canvas_hover_shows_a_tooltip_for_the_resolved_point(
    service_graphs: ServiceGraphs, javascript_errors: list[str]
) -> None:
    """Hovering the canvas resolves a point and lists its series in a tooltip."""
    graph = service_graphs.panel(0).graph

    graph.hover_canvas(0.5, 0.5)

    expect(graph.tooltip, "Hovering the canvas showed no tooltip").to_be_visible()
    rows = graph.tooltip_rows()
    assert rows, "The tooltip appeared without a single entry for the hovered point"
    for label, value in rows:
        assert label, f"A tooltip entry has no metric name: {rows}"
        assert value, f"Tooltip entry {label!r} has no value: {rows}"
    assert not javascript_errors, f"Uncaught JS errors during the hover: {javascript_errors}"
