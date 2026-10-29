#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import functools
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import cmk.ccc.debug
from cmk.discover_plugins import discover_all_plugins, DiscoveredPlugins, PluginGroup
from cmk.graphing.v1 import entry_point_prefixes as entry_point_prefixes_v1
from cmk.graphing.v1 import metrics as metrics_v1
from cmk.graphing.v1 import translations as translations_v1
from cmk.graphing.v2_unstable import (
    entry_point_prefixes as entry_point_prefixes_v2_unstable,
)
from cmk.graphing_engine import (
    ApiGraph,
    ApiPerfometer,
    PerfometerIndex,
    sort_registered_graph_plugins,
)
from cmk.gui.log import logger

type DiscoveredGraphingPlugins = DiscoveredPlugins[
    metrics_v1.Metric | ApiPerfometer | ApiGraph | translations_v1.Translation
]


@dataclass(frozen=True, kw_only=True)
class GraphingPlugins:
    discovered: DiscoveredGraphingPlugins
    metrics: Mapping[str, metrics_v1.Metric]
    perfometers: PerfometerIndex
    graphs: Sequence[ApiGraph]
    translations: Sequence[translations_v1.Translation]


@functools.cache
def graphing_plugins() -> GraphingPlugins:
    discovered = discover_all_plugins(
        PluginGroup.GRAPHING,
        dict(entry_point_prefixes_v1()) | dict(entry_point_prefixes_v2_unstable()),
        skip_wrong_types=False,
        raise_errors=cmk.ccc.debug.enabled(),
    )
    plugins = discovered.plugins.values()
    graphs = {plugin.name: plugin for plugin in plugins if isinstance(plugin, ApiGraph)}
    return GraphingPlugins(
        discovered=discovered,
        metrics={
            plugin.name: plugin for plugin in plugins if isinstance(plugin, metrics_v1.Metric)
        },
        perfometers=PerfometerIndex(
            {plugin.name: plugin for plugin in plugins if isinstance(plugin, ApiPerfometer)}
        ),
        graphs=[plugin for _name, plugin in sort_registered_graph_plugins(graphs)],
        translations=[
            plugin for plugin in plugins if isinstance(plugin, translations_v1.Translation)
        ],
    )


def registered_metrics() -> Mapping[str, metrics_v1.Metric]:
    return graphing_plugins().metrics


def registered_perfometers() -> PerfometerIndex:
    return graphing_plugins().perfometers


def registered_graphs() -> Sequence[ApiGraph]:
    return graphing_plugins().graphs


def registered_translations() -> Sequence[translations_v1.Translation]:
    return graphing_plugins().translations


def load_plugins() -> None:
    for exc in graphing_plugins().discovered.errors:
        logger.error(exc)
