#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Frequently used variable names:
# perf_data_string:   Raw performance data as sent by the core, e.g "foo=17M;1;2;4;5"
# perf_data:          Split performance data, e.g. [("foo", "17", "M", "1", "2", "4", "5")]
# translated_metrics: Completely parsed and translated into metrics, e.g. { "foo" : { "value" : 17.0, "unit" : { "render" : ... }, ... } }
# color:              RGB color representation ala HTML, e.g. "#ffbbc3" or "#FFBBC3", len() is always 7!
# color_rgb:          RGB color split into triple (r, g, b), where r,b,g in (0.0 .. 1.0)
# unit_name:          The ID of a unit, e.g. "%"
# unit:               The definition-dict of a unit like in unit_info
# graph_template:     Template for a graph. Essentially a dict with the key "metrics"

import json
from typing import override

import cmk.ccc.debug
import cmk.ccc.plugin_registry
from cmk.ccc.hostaddress import HostName
from cmk.ccc.site import SiteId

import cmk.utils
import cmk.utils.render
from cmk.utils.metrics import MetricName
from cmk.utils.servicename import ServiceName

import cmk.gui.pages
from cmk.gui.config import Config
from cmk.gui.graphing import _legacy as graphing_legacy
from cmk.gui.graphing._from_api import (
    graphs_from_api,
    metrics_from_api,
    parse_metric_from_api,
    perfometers_from_api,
)
from cmk.gui.graphing._graph_render_config import GraphRenderConfig
from cmk.gui.graphing._graph_specification import parse_raw_graph_specification
from cmk.gui.graphing._html_render import (
    host_service_graph_dashlet_cmk,
    host_service_graph_popup_cmk,
)
from cmk.gui.htmllib.html import html
from cmk.gui.http import request
from cmk.gui.log import logger
from cmk.gui.pages import PageResult

from cmk.discover_plugins import discover_all_plugins, DiscoveredPlugins, PluginGroup
from cmk.graphing.v1 import entry_point_prefixes
from cmk.graphing.v1 import graphs as graphs_api
from cmk.graphing.v1 import metrics as metrics_api
from cmk.graphing.v1 import perfometers as perfometers_api
from cmk.graphing.v1 import translations as translations_api

#   .--Plugins-------------------------------------------------------------.
#   |                   ____  _             _                              |
#   |                  |  _ \| |_   _  __ _(_)_ __  ___                    |
#   |                  | |_) | | | | |/ _` | | '_ \/ __|                   |
#   |                  |  __/| | |_| | (_| | | | | \__ \                   |
#   |                  |_|   |_|\__,_|\__, |_|_| |_|___/                   |
#   |                                 |___/                                |
#   +----------------------------------------------------------------------+
#   |  Typical code for loading Multisite plug-ins of this module           |
#   '----------------------------------------------------------------------'


def _load_graphing_plugins() -> DiscoveredPlugins[
    metrics_api.Metric
    | perfometers_api.Perfometer
    | perfometers_api.Bidirectional
    | perfometers_api.Stacked
    | graphs_api.Graph
    | graphs_api.Bidirectional
    | translations_api.Translation
]:
    discovered_plugins: DiscoveredPlugins[
        metrics_api.Metric
        | perfometers_api.Perfometer
        | perfometers_api.Bidirectional
        | perfometers_api.Stacked
        | graphs_api.Graph
        | graphs_api.Bidirectional
        | translations_api.Translation
    ] = discover_all_plugins(
        PluginGroup.GRAPHING,
        entry_point_prefixes(),
        raise_errors=cmk.ccc.debug.enabled(),
    )
    for exc in discovered_plugins.errors:
        logger.error(exc)
    return discovered_plugins


def _parse_check_command_from_api(
    check_command: (
        translations_api.PassiveCheck
        | translations_api.ActiveCheck
        | translations_api.HostCheckCommand
        | translations_api.NagiosPlugin
    ),
) -> str:
    match check_command:
        case translations_api.PassiveCheck():
            return (
                check_command.name
                if check_command.name.startswith("check_mk-")
                else f"check_mk-{check_command.name}"
            )
        case translations_api.ActiveCheck():
            return (
                check_command.name
                if check_command.name.startswith("check_mk_active-")
                else f"check_mk_active-{check_command.name}"
            )
        case translations_api.HostCheckCommand():
            return (
                check_command.name
                if check_command.name.startswith("check-mk-")
                else f"check-mk-{check_command.name}"
            )
        case translations_api.NagiosPlugin():
            return (
                check_command.name
                if check_command.name.startswith("check_")
                else f"check_{check_command.name}"
            )


def _parse_translation(
    translation: (
        translations_api.RenameTo | translations_api.ScaleBy | translations_api.RenameToAndScaleBy
    ),
) -> graphing_legacy.CheckMetricEntry:
    match translation:
        case translations_api.RenameTo():
            return {"name": translation.metric_name}
        case translations_api.ScaleBy():
            return {"scale": translation.factor}
        case translations_api.RenameToAndScaleBy():
            return {"name": translation.metric_name, "scale": translation.factor}


def _add_graphing_plugins(
    plugins: DiscoveredPlugins[
        metrics_api.Metric
        | perfometers_api.Perfometer
        | perfometers_api.Bidirectional
        | perfometers_api.Stacked
        | graphs_api.Graph
        | graphs_api.Bidirectional
        | translations_api.Translation
    ],
) -> None:
    for plugin in plugins.plugins.values():
        if isinstance(plugin, metrics_api.Metric):
            metrics_from_api.register(parse_metric_from_api(plugin))

        elif isinstance(plugin, translations_api.Translation):
            for check_command in plugin.check_commands:
                graphing_legacy.check_metrics[_parse_check_command_from_api(check_command)] = {
                    MetricName(old_name): _parse_translation(translation)
                    for old_name, translation in plugin.translations.items()
                }

        elif isinstance(
            plugin,
            perfometers_api.Perfometer | perfometers_api.Bidirectional | perfometers_api.Stacked,
        ):
            perfometers_from_api.register(plugin)

        elif isinstance(plugin, graphs_api.Graph | graphs_api.Bidirectional):
            graphs_from_api.register(plugin)


def load_plugins() -> None:
    """Plug-in initialization hook (Called by cmk.gui.main_modules.load_plugins())"""
    _add_graphing_plugins(_load_graphing_plugins())


class PageHostServiceGraphPopup(cmk.gui.pages.Page):
    @override
    def page(self, config: Config) -> PageResult:
        """This page is called for the popup of the graph icon of hosts/services."""
        host_service_graph_popup_cmk(
            SiteId(raw_site_id) if (raw_site_id := request.var("site")) else None,
            request.get_validated_type_input_mandatory(HostName, "host_name"),
            ServiceName(request.get_str_input_mandatory("service")),
            metrics_from_api,
            graphs_from_api,
        )
        return None  # for mypy


class PageGraphDashlet(cmk.gui.pages.Page):
    @override
    def page(self, config: Config) -> None:
        html.write_html(
            host_service_graph_dashlet_cmk(
                parse_raw_graph_specification(json.loads(request.get_str_input_mandatory("spec"))),
                GraphRenderConfig.model_validate_json(request.get_str_input_mandatory("config")),
                metrics_from_api,
                graphs_from_api,
                graph_display_id=request.get_str_input_mandatory("id"),
            )
        )
