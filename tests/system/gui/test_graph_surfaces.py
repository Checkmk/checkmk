#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Graph collection surface.

The cases assert what the engine renders, never what the legacy renderer no longer
does: a slot holds either a plot the engine drew or an error box, so a plot in every slot already
says the old renderer drew nothing.

The forecast surface lives in ``nonfree/pro/test_forecast_graph_engine.py``, since
forecast graphs are Pro+.
"""

import pytest
from playwright.sync_api import expect

from tests.system.gui.testlib.playwright.pom.graphing.fixtures import GRAPH_COLLECTION_SIZE
from tests.system.gui.testlib.playwright.pom.graphing.graph_collection import GraphCollection
from tests.system.gui.testlib.playwright.pom.monitor.dashboard import MainDashboard


@pytest.mark.skip_if_edition("community")
def test_graph_collection_renders_every_slot(
    dashboard_page: MainDashboard,
    graph_collection: str,
    javascript_errors: list[str],
) -> None:
    """Every graph in a collection renders through the new engine.

    One plot per slot and as many plots as the collection holds together say that every slot
    drew exactly one graph, without asserting per index which graph landed where.
    """
    collection = GraphCollection(dashboard_page.page, graph_collection)

    expect(
        collection.slots_holding_a_graph,
        "A slot of the collection holds no graph rendered by the new engine",
    ).to_have_count(GRAPH_COLLECTION_SIZE)
    expect(
        collection.drawn_plots,
        "A graph of the collection drew no plot on screen",
    ).to_have_count(GRAPH_COLLECTION_SIZE)
    assert not javascript_errors, (
        f"Opening the collection raised uncaught page errors: {javascript_errors}"
    )


@pytest.mark.skip_if_edition("community")
def test_graph_collection_has_no_broken_graphs(
    dashboard_page: MainDashboard,
    graph_collection: str,
    javascript_errors: list[str],
) -> None:
    """A graph collection renders with no broken graphs.

    The order matters. A graph the server cannot resolve never mounts a group at all, so its box
    is checked first; every graph reporting itself loaded then gates the engine's own failure
    states, which settle at the same moment, so each of them reports itself instead of surfacing
    as a missing graph.
    """
    collection = GraphCollection(dashboard_page.page, graph_collection)

    expect(
        collection.broken_graphs,
        "The server could not resolve every graph of the collection",
    ).to_have_count(0)
    expect(
        collection.slots_reporting_loaded,
        "A graph of the collection never reported itself loaded",
    ).to_have_count(GRAPH_COLLECTION_SIZE)
    expect(
        collection.error_notices,
        "A graph of the collection failed to load its data",
    ).to_have_count(0)
    expect(
        collection.skeletons,
        "A skeleton outlived the graph it was standing in for",
    ).to_have_count(0)
    assert not javascript_errors, (
        f"Rendering the collection raised uncaught page errors: {javascript_errors}"
    )
