#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Rendering engine: hover tooltip, theme, resize (R1.2).

Skipped skeletons (CMK-35973). Complete once the engine renders: reach the graph via
GraphAccessor.graph_root and assert through the page-objects in timeseries_graph.py.
``graph_hosts_with_varying_data`` supplies hosts with real metric data.

"""

import pytest

from tests.gui_e2e.testlib.playwright.pom.monitor.dashboard import MainDashboard
from tests.testlib.graphing import SKIP_PENDING_GRAPH_ENGINE


@pytest.mark.skip(reason=SKIP_PENDING_GRAPH_ENGINE)
def test_hover_tooltip_shows_metric_name_and_value(
    dashboard_page: MainDashboard, graph_hosts_with_varying_data: list[str]
) -> None:
    """LT-02 (R1.2 Area 5): hovering shows a tooltip with a name and value.

    Do: move the cursor to the canvas centre (page.mouse.move).
    Assert: tooltip visible with a non-empty metric name and a numeric value+unit, or "n/a".
    """
    pytest.fail("CMK-35973 skeleton: body not implemented")


@pytest.mark.skip(reason=SKIP_PENDING_GRAPH_ENGINE)
def test_hover_emphasises_nearest_series(
    dashboard_page: MainDashboard, graph_hosts_with_varying_data: list[str]
) -> None:
    """LT-03 (R1.2 Area 5): the tooltip emphasises the nearest series.

    Do: for a multi-series graph, move the cursor close to one series line.
    Assert: that series' tooltip entry is emphasised relative to the others.
    """
    pytest.fail("CMK-35973 skeleton: body not implemented")


@pytest.mark.skip(reason=SKIP_PENDING_GRAPH_ENGINE)
def test_graph_renders_in_dark_mode(
    dashboard_page: MainDashboard, graph_hosts_with_varying_data: list[str]
) -> None:
    """TM-01 (R1.2 Area 7): in dark mode every element is visible with distinct fg/bg.

    Do: set dark mode; open a service detail graph.
    Assert: component, canvas and SVG children visible; no element has fg == bg; no JS error.
    """
    pytest.fail("CMK-35973 skeleton: body not implemented")


@pytest.mark.skip(reason=SKIP_PENDING_GRAPH_ENGINE)
def test_graph_renders_in_light_mode(
    dashboard_page: MainDashboard, graph_hosts_with_varying_data: list[str]
) -> None:
    """TM-02 (R1.2 Area 7): in light mode the graph renders without errors.

    Do: with light mode (default), open the same graph.
    Assert: no JS error; component, canvas and SVG children visible.
    """
    pytest.fail("CMK-35973 skeleton: body not implemented")


@pytest.mark.skip(reason=SKIP_PENDING_GRAPH_ENGINE)
def test_canvas_redraws_on_viewport_resize_without_refetch(
    dashboard_page: MainDashboard, graph_hosts_with_varying_data: list[str]
) -> None:
    """RZ-01 (R1.2 Area 9): a resize redraws the canvas without a data request.

    Do: open a graph, record the canvas width, register a page.route intercept, resize narrower.
    Assert: canvas width matches the new container; no new graph-data request; no JS error.
    """
    pytest.fail("CMK-35973 skeleton: body not implemented")
