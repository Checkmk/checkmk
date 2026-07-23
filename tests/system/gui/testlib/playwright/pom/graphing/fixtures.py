#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Reusable fixtures for the graph E2E suites.

Registered for discovery in ``tests/system/gui/conftest.py``. The saved-surface
fixtures (custom graph, collection, forecast) `skip` until completed by the graph
test suites, since creating and surfacing them depends on the graph implementation.
"""

import pytest

from tests.testlib.graphing import InjectedRrd
from tests.testlib.site import Site


@pytest.fixture(name="graph_hosts_with_varying_data", scope="module")
def fixture_graph_hosts_with_varying_data(linux_hosts: list[str]) -> list[str]:
    """Hosts whose real agent data yields graphs with varying values."""
    return linux_hosts


@pytest.fixture(name="graph_hosts_high_density", scope="module")
def fixture_graph_hosts_high_density(test_site: Site) -> list[str]:
    """Monitored hosts/services with high-density graph data.

    For performance/loading/legend/tooltip cases: a graph near the engine's
    ceiling (~1M points) and/or many series (200+ metrics). `inject_rrd` covers
    the point-count dimension (it writes one series); the many-series dimension
    needs a host carrying many real metrics.
    """
    pytest.skip("graph_hosts_high_density is scaffolding: seed a high-density monitored service.")


@pytest.fixture(name="graph_rrd_with_gaps", scope="module")
def fixture_graph_rrd_with_gaps(test_site: Site) -> InjectedRrd:
    """An RRD with missing samples; inject via `graphing.inject_rrd` (GAPS)."""
    pytest.skip("graph_rrd_with_gaps is scaffolding: bind inject_rrd to a monitored service.")


@pytest.fixture(name="graph_rrd_dst_boundary", scope="module")
def fixture_graph_rrd_dst_boundary(test_site: Site) -> InjectedRrd:
    """An RRD whose rendered window crosses a DST transition.

    DST is a timezone/window concern, not a data shape: set the user timezone to
    a DST-observing zone (e.g. Europe/Berlin) and inject `VARYING` data starting
    at `graphing.DST_FALL_BACK_BERLIN_UTC`, bound to a monitored service.
    Use the fall-back instant: it makes local 02:00-02:59 occur twice, which is
    what the "no duplicate X-axis labels" regression (Werk #14830) needs;
    spring-forward only skips the hour and would not exercise it.
    """
    pytest.skip("graph_rrd_dst_boundary is scaffolding: see docstring.")


@pytest.fixture(name="saved_custom_graph")
def fixture_saved_custom_graph(test_site: Site) -> str:
    """A saved custom graph; complete via the custom-graph creation flow."""
    pytest.skip("saved_custom_graph is scaffolding: graph engine not implemented yet.")


@pytest.fixture(name="graph_collection")
def fixture_graph_collection(test_site: Site) -> str:
    """A saved graph collection; complete via the graph-collection creation flow."""
    pytest.skip("graph_collection is scaffolding: graph engine not implemented yet.")


@pytest.fixture(name="forecast_graph")
def fixture_forecast_graph(test_site: Site) -> str:
    """A saved forecast graph; complete via the forecast-graph creation flow."""
    pytest.skip("forecast_graph is scaffolding: graph engine not implemented yet.")
