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
import cmk.gui.pages
from cmk.ccc.hostaddress import HostName
from cmk.ccc.site import SiteId
from cmk.ccc.version import edition
from cmk.discover_plugins import discover_all_plugins, DiscoveredPlugins, PluginGroup
from cmk.graphing.v1 import entry_point_prefixes
from cmk.graphing.v1 import graphs as graphs_api
from cmk.graphing.v1 import metrics as metrics_api
from cmk.graphing.v1 import perfometers as perfometers_api
from cmk.graphing.v1 import translations as translations_api
from cmk.gui.graphing import (
    check_metrics,
    CheckMetricEntry,
    get_temperature_unit,
    GraphRenderConfig,
    graphs_from_api,
    host_service_graph_dashlet_cmk,
    host_service_graph_popup_cmk,
    metric_backend_registry,
    metrics_from_api,
    MKGraphDashletTooSmallError,
    MKGraphRecipeCalculationError,
    MKGraphRecipeNotFoundError,
    parse_metric_from_api,
    parse_raw_graph_specification,
    perfometers_from_api,
)
from cmk.gui.htmllib.html import html
from cmk.gui.log import logger
from cmk.gui.logged_in import user
from cmk.gui.pages import PageContext, PageResult
from cmk.gui.permissions import permission_registry
from cmk.gui.utils.roles import UserPermissions
from cmk.utils import paths
from cmk.utils.metrics import MetricName
from cmk.utils.servicename import ServiceName

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
) -> CheckMetricEntry:
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
                check_metrics[_parse_check_command_from_api(check_command)] = {
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


def register() -> None:
    _add_graphing_plugins(_load_graphing_plugins())


class PageHostServiceGraphPopup(cmk.gui.pages.Page):
    @override
    def page(self, ctx: PageContext) -> PageResult:
        """This page is called for the popup of the graph icon of hosts/services."""
        host_service_graph_popup_cmk(
            ctx.request,
            SiteId(raw_site_id) if (raw_site_id := ctx.request.var("site")) else None,
            ctx.request.get_validated_type_input_mandatory(HostName, "host_name"),
            ServiceName(ctx.request.get_str_input_mandatory("service")),
            metrics_from_api,
            graphs_from_api,
            UserPermissions.from_config(ctx.config, permission_registry),
            debug=ctx.config.debug,
            graph_timeranges=ctx.config.graph_timeranges,
            temperature_unit=get_temperature_unit(user, ctx.config.default_temperature_unit),
            backend_time_series_fetcher=metric_backend_registry[
                str(edition(paths.omd_root))
            ].get_time_series_fetcher(ctx.config),
        )
        return None  # for mypy


class PageGraphDashlet(cmk.gui.pages.Page):
    @override
    def page(self, ctx: PageContext) -> None:
        try:
            html.write_html(
                host_service_graph_dashlet_cmk(
                    ctx.request,
                    parse_raw_graph_specification(
                        json.loads(ctx.request.get_str_input_mandatory("spec"))
                    ),
                    GraphRenderConfig.model_validate_json(
                        ctx.request.get_str_input_mandatory("config")
                    ),
                    metrics_from_api,
                    graphs_from_api,
                    UserPermissions.from_config(ctx.config, permission_registry),
                    debug=ctx.config.debug,
                    graph_timeranges=ctx.config.graph_timeranges,
                    temperature_unit=get_temperature_unit(
                        user, ctx.config.default_temperature_unit
                    ),
                    backend_time_series_fetcher=metric_backend_registry[
                        str(edition(paths.omd_root))
                    ].get_time_series_fetcher(ctx.config),
                    graph_display_id=ctx.request.get_str_input_mandatory("id"),
                )
            )
        except (
            MKGraphRecipeCalculationError,
            MKGraphRecipeNotFoundError,
            MKGraphDashletTooSmallError,
        ) as e:
            html.write_html(html.render_message(str(e)))
