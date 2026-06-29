#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from __future__ import annotations

import functools
from collections.abc import Mapping, Sequence

from cmk.discover_plugins import discover_all_plugins, DiscoveredPlugins, PluginGroup
from cmk.graphing.v1 import entry_point_prefixes as entry_point_prefixes_v1
from cmk.graphing.v1 import graphs as graphs_v1
from cmk.graphing.v1 import metrics as metrics_v1
from cmk.graphing.v1 import translations as translations_v1
from cmk.graphing.v2_unstable import (
    entry_point_prefixes as entry_point_prefixes_v2_unstable,
)
from cmk.graphing.v2_unstable import graphs as graphs_v2_unstable

from ._from_api import GraphFromAPI, PerfometerFromAPI
from ._graph_templates import sort_registered_graph_plugins

# The graph types the engine accepts; used to pick graph plugins out of the discovered set.
_GRAPH_TYPES = (
    graphs_v1.Graph,
    graphs_v1.Bidirectional,
    graphs_v2_unstable.Graph,
    graphs_v2_unstable.Bidirectional,
)


@functools.cache
def _graphing_plugins() -> DiscoveredPlugins[
    metrics_v1.Metric | PerfometerFromAPI | GraphFromAPI | translations_v1.Translation
]:
    return discover_all_plugins(
        PluginGroup.GRAPHING,
        dict(entry_point_prefixes_v1()) | dict(entry_point_prefixes_v2_unstable()),
        skip_wrong_types=False,
        raise_errors=False,
    )


def registered_metrics() -> Mapping[str, metrics_v1.Metric]:
    return {
        plugin.name: plugin
        for plugin in _graphing_plugins().plugins.values()
        if isinstance(plugin, metrics_v1.Metric)
    }


def registered_graphs() -> Sequence[GraphFromAPI]:
    # Emit graphs in the legacy discovery order (cf. sort_registered_graph_plugins): ordered by
    # GRAPHS_ORDER, with any graph not listed there kept ahead of the ordered ones.
    registered = {
        plugin.name: plugin
        for plugin in _graphing_plugins().plugins.values()
        if isinstance(plugin, _GRAPH_TYPES)
    }
    return [plugin for _name, plugin in sort_registered_graph_plugins(registered)]


def registered_translations() -> Sequence[translations_v1.Translation]:
    return [
        plugin
        for plugin in _graphing_plugins().plugins.values()
        if isinstance(plugin, translations_v1.Translation)
    ]
