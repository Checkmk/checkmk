#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import cmk.utils.debug

from cmk.discover_plugins import discover_plugins, DiscoveredPlugins, PluginGroup
from cmk.graphing.v1 import graphs, metrics, perfometers, translations


def load_graphing_plugins() -> (
    DiscoveredPlugins[
        metrics.Metric
        | translations.Translation
        | perfometers.Perfometer
        | perfometers.Bidirectional
        | perfometers.Stacked
        | graphs.Graph
        | graphs.Bidirectional
    ]
):
    return discover_plugins(
        PluginGroup.GRAPHING,
        {
            metrics.Metric: "metric_",
            translations.Translation: "translation_",
            perfometers.Perfometer: "perfometer_",
            perfometers.Bidirectional: "perfometer_",
            perfometers.Stacked: "perfometer_",
            graphs.Graph: "graph_",
            graphs.Bidirectional: "graph_",
        },
        raise_errors=cmk.utils.debug.enabled(),
    )
