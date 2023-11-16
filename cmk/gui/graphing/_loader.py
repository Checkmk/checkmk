#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import cmk.utils

from cmk.discover_plugins import discover_plugins, DiscoveredPlugins
from cmk.graphing.v1 import graph, metric, perfometer, translation


def load_graphing_plugins() -> (
    DiscoveredPlugins[
        metric.Metric
        | translation.Translation
        | perfometer.Perfometer
        | perfometer.Bidirectional
        | perfometer.Stacked
        | graph.Graph
        | graph.Bidirectional
    ]
):
    return discover_plugins(
        "graphing",
        {
            metric.Metric: "metric_",
            translation.Translation: "translation_",
            perfometer.Perfometer: "perfometer_",
            perfometer.Bidirectional: "perfometer_",
            perfometer.Stacked: "perfometer_",
            graph.Graph: "graph_",
            graph.Bidirectional: "graph_",
        },
        raise_errors=cmk.utils.debug.enabled(),
    )
