#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.graphing.v1 import graphs as graphs_v1
from cmk.graphing.v1 import metrics as metrics_v1
from cmk.graphing.v1 import perfometers as perfometers_v1
from cmk.graphing.v2_unstable import graphs as graphs_v2_unstable
from cmk.graphing.v2_unstable import perfometers as perfometers_v2_unstable
from cmk.gui.log import logger

from ._from_api import (
    graphs_from_api,
    metrics_from_api,
    parse_metric_from_api,
    perfometers_from_api,
)
from ._plugins import graphing_plugins, GraphingPlugins


def _add_graphing_plugins(plugins: GraphingPlugins) -> None:
    for plugin in plugins.plugins.values():
        if isinstance(plugin, metrics_v1.Metric):
            metrics_from_api.register(parse_metric_from_api(plugin))

        elif isinstance(
            plugin,
            perfometers_v1.Perfometer
            | perfometers_v1.Bidirectional
            | perfometers_v1.Stacked
            | perfometers_v2_unstable.Perfometer
            | perfometers_v2_unstable.Bidirectional
            | perfometers_v2_unstable.Stacked,
        ):
            perfometers_from_api.register(plugin)

        elif isinstance(
            plugin,
            graphs_v1.Graph
            | graphs_v1.Bidirectional
            | graphs_v2_unstable.Graph
            | graphs_v2_unstable.Bidirectional,
        ):
            graphs_from_api.register(plugin)


def register_plugins() -> None:
    plugins = graphing_plugins()
    for exc in plugins.errors:
        logger.error(exc)
    _add_graphing_plugins(plugins)
