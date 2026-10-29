#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import functools
from collections.abc import Mapping, Sequence

from cmk.discover_plugins import discover_all_plugins, DiscoveredPlugins, PluginGroup
from cmk.graphing.v1 import entry_point_prefixes as entry_point_prefixes_v1
from cmk.graphing.v1 import metrics as metrics_v1
from cmk.graphing.v1 import translations as translations_v1
from cmk.graphing.v2_unstable import (
    entry_point_prefixes as entry_point_prefixes_v2_unstable,
)
from cmk.graphing_engine import (
    ApiGraph,
    ApiGraphingPlugin,
    graphing_plugins_of,
    GraphingPlugins,
    PerfometerIndex,
)
from cmk.gui.log import logger


@functools.cache
def discovered_graphing_plugins(*, debug: bool) -> DiscoveredPlugins[ApiGraphingPlugin]:
    return discover_all_plugins(
        PluginGroup.GRAPHING,
        dict(entry_point_prefixes_v1()) | dict(entry_point_prefixes_v2_unstable()),
        skip_wrong_types=False,
        raise_errors=debug,
    )


@functools.cache
def graphing_plugins() -> GraphingPlugins:
    return graphing_plugins_of(discovered_graphing_plugins(debug=False).plugins.values())


def registered_metrics() -> Mapping[str, metrics_v1.Metric]:
    return graphing_plugins().metrics


def registered_perfometers() -> PerfometerIndex:
    return graphing_plugins().perfometers


def registered_graphs() -> Sequence[ApiGraph]:
    return graphing_plugins().graphs


def registered_translations() -> Sequence[translations_v1.Translation]:
    return graphing_plugins().translations


def load_plugins(*, debug: bool) -> None:
    for exc in discovered_graphing_plugins(debug=debug).errors:
        logger.error(exc)
