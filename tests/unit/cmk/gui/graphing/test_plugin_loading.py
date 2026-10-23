#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.discover_plugins import DiscoveredPlugins, PluginLocation
from cmk.graphing import v1 as graphing_api
from cmk.graphing.v1 import graphs as graphs_api
from cmk.graphing.v1 import metrics as metrics_api
from cmk.gui.graphing import (
    get_graph_plugin_from_id,
    graphs_from_api,
)
from cmk.gui.graphing._plugin_loading import _add_graphing_plugins


def test_add_graphing_plugins_registers_the_graphs_among_the_plugins() -> None:
    test_metric_1 = metrics_api.Metric(
        name="syntest_count_first",
        title=graphing_api.Title("Synthetic test count (first)"),
        unit=metrics_api.Unit(
            metrics_api.DecimalNotation(""),
            metrics_api.StrictPrecision(2),
        ),
        color=metrics_api.Color.PURPLE,
    )
    test_metric_2 = metrics_api.Metric(
        name="syntest_count_second",
        title=graphing_api.Title("Synthetic test count (second)"),
        unit=metrics_api.Unit(
            metrics_api.DecimalNotation(""),
            metrics_api.StrictPrecision(2),
        ),
        color=metrics_api.Color.BLUE,
    )
    test_graph = graphs_api.Graph(
        name="syntest_counts",
        title=graphing_api.Title("Synthetic test counts"),
        simple_lines=[
            "syntest_count_first",
            "syntest_count_second",
            metrics_api.WarningOf("syntest_count_first"),
            metrics_api.CriticalOf("syntest_count_first"),
        ],
    )
    _add_graphing_plugins(
        DiscoveredPlugins(
            errors=[],
            plugins={
                PluginLocation("syntest", "metric_1"): test_metric_1,
                PluginLocation("syntest", "metric_2"): test_metric_2,
                PluginLocation("syntest", "graph"): test_graph,
            },
            conflicts=(),
            errors_by_module={},
        )
    )

    assert get_graph_plugin_from_id(graphs_from_api, "syntest_counts") == graphs_api.Graph(
        name="syntest_counts",
        title=graphing_api.Title("Synthetic test counts"),
        simple_lines=[
            "syntest_count_first",
            "syntest_count_second",
            metrics_api.WarningOf("syntest_count_first"),
            metrics_api.CriticalOf("syntest_count_first"),
        ],
    )
