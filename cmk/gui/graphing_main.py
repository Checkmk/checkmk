#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import override

import cmk.ccc.debug
import cmk.gui.pages
from cmk.ccc.hostaddress import HostName
from cmk.ccc.site import SiteId
from cmk.discover_plugins import discover_all_plugins, DiscoveredPlugins, PluginGroup
from cmk.graphing.v1 import entry_point_prefixes as entry_point_prefixes_v1
from cmk.graphing.v1 import graphs as graphs_v1
from cmk.graphing.v1 import metrics as metrics_v1
from cmk.graphing.v1 import perfometers as perfometers_v1
from cmk.graphing.v1 import translations as translations_v1
from cmk.graphing.v2_unstable import entry_point_prefixes as entry_point_prefixes_v2_unstable
from cmk.graphing.v2_unstable import graphs as graphs_v2_unstable
from cmk.graphing.v2_unstable import perfometers as perfometers_v2_unstable
from cmk.gui.graphing import (
    GraphFromAPI,
    graphs_from_api,
    host_service_graph_popup_cmk,
    metrics_from_api,
    parse_metric_from_api,
    PerfometerFromAPI,
    perfometers_from_api,
)
from cmk.gui.log import logger
from cmk.gui.pages import PageContext, PageResult
from cmk.utils.servicename import ServiceName


def _load_graphing_plugins() -> DiscoveredPlugins[
    metrics_v1.Metric | PerfometerFromAPI | GraphFromAPI | translations_v1.Translation
]:
    discovered_plugins: DiscoveredPlugins[
        metrics_v1.Metric | PerfometerFromAPI | GraphFromAPI | translations_v1.Translation
    ] = discover_all_plugins(
        PluginGroup.GRAPHING,
        dict(entry_point_prefixes_v1()) | dict(entry_point_prefixes_v2_unstable()),
        skip_wrong_types=False,
        raise_errors=cmk.ccc.debug.enabled(),
    )
    for exc in discovered_plugins.errors:
        logger.error(exc)
    return discovered_plugins


def _add_graphing_plugins(
    plugins: DiscoveredPlugins[
        metrics_v1.Metric | PerfometerFromAPI | GraphFromAPI | translations_v1.Translation
    ],
) -> None:
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


def register() -> None:
    _add_graphing_plugins(_load_graphing_plugins())


class PageHostServiceGraphPopup(cmk.gui.pages.Page):
    @override
    def page(self, ctx: PageContext) -> PageResult:
        """This page is called for the popup of the graph icon of hosts/services."""
        host_service_graph_popup_cmk(
            SiteId(raw_site_id) if (raw_site_id := ctx.request.var("site")) else None,
            ctx.request.get_validated_type_input_mandatory(HostName, "host_name"),
            ServiceName(ctx.request.get_str_input_mandatory("service")),
            debug=ctx.config.debug,
        )
        return None  # for mypy
