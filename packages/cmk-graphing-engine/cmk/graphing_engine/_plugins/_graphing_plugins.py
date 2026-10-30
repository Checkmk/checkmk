#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass

from cmk.graphing.v1 import metrics as metrics_v1
from cmk.graphing.v1 import translations as translations_v1

from ._order import sort_registered_graph_plugins
from ._perfometer_matching import PerfometerIndex
from ._types import ApiGraph, ApiPerfometer

type ApiGraphingPlugin = metrics_v1.Metric | ApiPerfometer | ApiGraph | translations_v1.Translation


@dataclass(frozen=True, kw_only=True)
class GraphingPlugins:
    metrics: Mapping[str, metrics_v1.Metric]
    perfometers: PerfometerIndex
    graphs: Sequence[ApiGraph]
    translations: Sequence[translations_v1.Translation]


def graphing_plugins_of(plugins: Collection[ApiGraphingPlugin]) -> GraphingPlugins:
    graphs = {plugin.name: plugin for plugin in plugins if isinstance(plugin, ApiGraph)}
    return GraphingPlugins(
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
