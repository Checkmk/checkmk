#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.graphing._loader import load_graphing_plugins
from cmk.gui.graphing._utils import graph_info, metric_info

from cmk.graphing.v1 import graphs, metrics


def test_load_graphing_plugins() -> None:
    discovered_graphing_plugins = load_graphing_plugins()
    assert not discovered_graphing_plugins.errors
    assert discovered_graphing_plugins.plugins


def test_metric_duplicates() -> None:
    assert metric_info
    metric_names = {
        p.name for p in load_graphing_plugins().plugins.values() if isinstance(p, metrics.Metric)
    }
    assert not set(metric_info).intersection(metric_names)


def test_graph_duplicates() -> None:
    assert graph_info
    graph_names = {
        p.name
        for p in load_graphing_plugins().plugins.values()
        if isinstance(p, (graphs.Graph, graphs.Bidirectional))
    }
    assert not set(graph_info).intersection(graph_names)
