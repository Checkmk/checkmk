#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import functools
from collections.abc import Mapping, Sequence

import cmk.ccc.debug
from cmk.discover_plugins import discover_all_plugins, DiscoveredPlugins, PluginGroup
from cmk.graphing.v1 import entry_point_prefixes as entry_point_prefixes_v1
from cmk.graphing.v1 import metrics as metrics_v1
from cmk.graphing.v1 import translations as translations_v1
from cmk.graphing.v2_unstable import (
    entry_point_prefixes as entry_point_prefixes_v2_unstable,
)
from cmk.graphing_engine import ApiGraph, ApiPerfometer

from ._graphs_order import sort_registered_graph_plugins

type GraphingPlugins = DiscoveredPlugins[
    metrics_v1.Metric | ApiPerfometer | ApiGraph | translations_v1.Translation
]


@functools.cache
def graphing_plugins() -> GraphingPlugins:
    return discover_all_plugins(
        PluginGroup.GRAPHING,
        dict(entry_point_prefixes_v1()) | dict(entry_point_prefixes_v2_unstable()),
        skip_wrong_types=False,
        raise_errors=cmk.ccc.debug.enabled(),
    )


def registered_metrics() -> Mapping[str, metrics_v1.Metric]:
    return {
        plugin.name: plugin
        for plugin in graphing_plugins().plugins.values()
        if isinstance(plugin, metrics_v1.Metric)
    }


def registered_graphs() -> Sequence[ApiGraph]:
    # Emit graphs in the legacy discovery order (cf. sort_registered_graph_plugins): ordered by
    # GRAPHS_ORDER, with any graph not listed there kept ahead of the ordered ones.
    registered = {
        plugin.name: plugin
        for plugin in graphing_plugins().plugins.values()
        if isinstance(plugin, ApiGraph)
    }
    return [plugin for _name, plugin in sort_registered_graph_plugins(registered)]


def registered_translations() -> Sequence[translations_v1.Translation]:
    return [
        plugin
        for plugin in graphing_plugins().plugins.values()
        if isinstance(plugin, translations_v1.Translation)
    ]
