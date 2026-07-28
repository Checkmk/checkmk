#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Forecast graph and graph collection surfaces (R1.3 Areas 6, 7). Skipped (CMK-35973).

Complete once the engine renders on these surfaces: reach them via the ForecastGraph /
GraphCollection POMs and GraphAccessor.graph_root.
"""

import pytest

from tests.gui_e2e.testlib.playwright.pom.monitor.dashboard import MainDashboard
from tests.testlib.graphing import SKIP_PENDING_GRAPH_ENGINE


@pytest.mark.skip(reason=SKIP_PENDING_GRAPH_ENGINE)
def test_forecast_graph_shows_historical_and_forecast_series(
    dashboard_page: MainDashboard, forecast_graph: str
) -> None:
    """FG-02 (R1.3 Area 6): the forecast graph shows historical and forecast series.

    Do: inspect the rendered forecast component.
    Assert: legend entries for both the historical and forecast series; no broken-graph.
    """
    pytest.fail("CMK-35973 skeleton: body not implemented")


@pytest.mark.skip(reason=SKIP_PENDING_GRAPH_ENGINE)
def test_graph_collection_renders_every_slot(
    dashboard_page: MainDashboard, graph_collection: str
) -> None:
    """GC-01 (R1.3 Area 7): every graph in a collection renders.

    Do: navigate to a saved graph collection (>=2 graphs).
    Assert: every slot has a rendered graph; no JS errors.
    """
    pytest.fail("CMK-35973 skeleton: body not implemented")


@pytest.mark.skip(reason=SKIP_PENDING_GRAPH_ENGINE)
def test_graph_collection_has_no_broken_graphs(
    dashboard_page: MainDashboard, graph_collection: str
) -> None:
    """GC-02 (R1.3 Area 7): a graph collection renders with no broken graphs.

    Do: navigate to the same collection; count broken-graph indicators.
    Assert: zero broken-graph elements; each component reports loaded.
    """
    pytest.fail("CMK-35973 skeleton: body not implemented")
