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
from collections.abc import Mapping
from typing import Any

from livestatus import SiteId

import cmk.utils
import cmk.utils.plugin_registry
import cmk.utils.render
from cmk.utils.hostaddress import HostName
from cmk.utils.servicename import ServiceName

import cmk.gui.pages
from cmk.gui import utils
from cmk.gui.config import Config
from cmk.gui.graphing import _color as graphing_color
from cmk.gui.graphing import _unit_info as graphing_unit_info
from cmk.gui.graphing import _utils as graphing_utils
from cmk.gui.graphing import perfometer_info
from cmk.gui.graphing._graph_render_config import GraphRenderConfig
from cmk.gui.graphing._graph_specification import parse_raw_graph_specification
from cmk.gui.graphing._html_render import (
    host_service_graph_dashlet_cmk,
    host_service_graph_popup_cmk,
)
from cmk.gui.graphing._loader import load_graphing_plugins
from cmk.gui.graphing._type_defs import TranslatedMetric
from cmk.gui.graphing._utils import (
    add_graphing_plugins,
    parse_perf_data,
    parse_perf_data_from_performance_data_livestatus_column,
    translate_metrics,
)
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.pages import PageResult

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


def load_plugins() -> None:
    """Plug-in initialization hook (Called by cmk.gui.main_modules.load_plugins())"""
    _register_pre_21_plugin_api()
    utils.load_web_plugins("metrics", globals())
    add_graphing_plugins(load_graphing_plugins())


def _register_pre_21_plugin_api() -> None:
    """Register pre 2.1 "plug-in API"

    This was never an official API, but the names were used by built-in and also 3rd party plugins.

    Our built-in plug-in have been changed to directly import from the .utils module. We add these old
    names to remain compatible with 3rd party plug-ins for now.

    In the moment we define an official plug-in API, we can drop this and require all plug-ins to
    switch to the new API. Until then let's not bother the users with it.

    CMK-12228
    """
    # Needs to be a local import to not influence the regular plug-in loading order
    import cmk.gui.plugins.metrics as legacy_api_module  # pylint: disable=cmk-module-layer-violation
    import cmk.gui.plugins.metrics.utils as legacy_plugin_utils  # pylint: disable=cmk-module-layer-violation

    for name in (
        "check_metrics",
        "G",
        "GB",
        "graph_info",
        "GraphTemplate",
        "K",
        "KB",
        "m",
        "M",
        "MAX_CORES",
        "MAX_NUMBER_HOPS",
        "MB",
        "metric_info",
        "P",
        "PB",
        "scale_symbols",
        "skype_mobile_devices",
        "T",
        "TB",
    ):
        legacy_api_module.__dict__[name] = graphing_utils.__dict__[name]
        legacy_plugin_utils.__dict__[name] = graphing_utils.__dict__[name]

    legacy_api_module.__dict__["perfometer_info"] = perfometer_info
    legacy_plugin_utils.__dict__["perfometer_info"] = perfometer_info

    legacy_api_module.__dict__["unit_info"] = graphing_unit_info.__dict__["unit_info"]
    legacy_plugin_utils.__dict__["unit_info"] = graphing_unit_info.__dict__["unit_info"]

    for name in (
        "darken_color",
        "indexed_color",
        "lighten_color",
        "MONITORING_STATUS_COLORS",
        "parse_color",
        "parse_color_into_hexrgb",
        "render_color",
        "scalar_colors",
    ):
        legacy_api_module.__dict__[name] = graphing_color.__dict__[name]
        legacy_plugin_utils.__dict__[name] = graphing_color.__dict__[name]

    # Avoid needed imports, see CMK-12147
    globals().update(
        {
            "indexed_color": graphing_color.indexed_color,
            "metric_info": graphing_utils.metric_info,
            "check_metrics": graphing_utils.check_metrics,
            "graph_info": graphing_utils.graph_info,
            "_": _,
        }
    )


# .
#   .--Helpers-------------------------------------------------------------.
#   |                  _   _      _                                        |
#   |                 | | | | ___| |_ __   ___ _ __ ___                    |
#   |                 | |_| |/ _ \ | '_ \ / _ \ '__/ __|                   |
#   |                 |  _  |  __/ | |_) |  __/ |  \__ \                   |
#   |                 |_| |_|\___|_| .__/ \___|_|  |___/                   |
#   |                              |_|                                     |
#   +----------------------------------------------------------------------+
#   |  Various helper functions                                            |
#   '----------------------------------------------------------------------'
# A few helper function to be used by the definitions


def metric_to_text(metric: dict[str, Any], value: int | float | None = None) -> str:
    if value is None:
        value = metric["value"]
    return metric["unit"]["render"](value)


# aliases to be compatible to old plugins
physical_precision = cmk.utils.render.physical_precision
age_human_readable = cmk.utils.render.approx_age

# .
#   .--Evaluation----------------------------------------------------------.
#   |          _____            _             _   _                        |
#   |         | ____|_   ____ _| |_   _  __ _| |_(_) ___  _ __             |
#   |         |  _| \ \ / / _` | | | | |/ _` | __| |/ _ \| '_ \            |
#   |         | |___ \ V / (_| | | |_| | (_| | |_| | (_) | | | |           |
#   |         |_____| \_/ \__,_|_|\__,_|\__,_|\__|_|\___/|_| |_|           |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |  Parsing of performance data into metrics, evaluation of expressions |
#   '----------------------------------------------------------------------'


def translate_perf_data(
    perf_data_string: str,
    *,
    config: Config,
    check_command: str | None = None,
) -> Mapping[str, TranslatedMetric]:
    perf_data, check_command = parse_perf_data(
        perf_data_string,
        check_command,
        config=config,
    )
    return translate_metrics(perf_data, check_command)


def translate_perf_data_from_performance_data_livestatus_column(
    perf_data_mapping: Mapping[str, float], check_command: str | None = None
) -> Mapping[str, TranslatedMetric]:
    perf_data, check_command = parse_perf_data_from_performance_data_livestatus_column(
        perf_data_mapping, check_command
    )
    return translate_metrics(perf_data, check_command)


# .
#   .--Hover-Graph---------------------------------------------------------.
#   |     _   _                           ____                 _           |
#   |    | | | | _____   _____ _ __      / ___|_ __ __ _ _ __ | |__        |
#   |    | |_| |/ _ \ \ / / _ \ '__|____| |  _| '__/ _` | '_ \| '_ \       |
#   |    |  _  | (_) \ V /  __/ | |_____| |_| | | | (_| | |_) | | | |      |
#   |    |_| |_|\___/ \_/ \___|_|        \____|_|  \__,_| .__/|_| |_|      |
#   |                                                   |_|                |
#   '----------------------------------------------------------------------'


# This page is called for the popup of the graph icon of hosts/services.
class PageHostServiceGraphPopup(cmk.gui.pages.Page):
    @classmethod
    def ident(cls) -> str:
        return "host_service_graph_popup"

    def page(self) -> PageResult:  # pylint: disable=useless-return
        host_service_graph_popup_cmk(
            SiteId(raw_site_id) if (raw_site_id := request.var("site")) else None,
            request.get_validated_type_input_mandatory(HostName, "host_name"),
            ServiceName(request.get_str_input_mandatory("service")),
        )
        return None  # for mypy


# .
#   .--Graph Dashlet-------------------------------------------------------.
#   |    ____                 _       ____            _     _      _       |
#   |   / ___|_ __ __ _ _ __ | |__   |  _ \  __ _ ___| |__ | | ___| |_     |
#   |  | |  _| '__/ _` | '_ \| '_ \  | | | |/ _` / __| '_ \| |/ _ \ __|    |
#   |  | |_| | | | (_| | |_) | | | | | |_| | (_| \__ \ | | | |  __/ |_     |
#   |   \____|_|  \__,_| .__/|_| |_| |____/ \__,_|___/_| |_|_|\___|\__|    |
#   |                  |_|                                                 |
#   +----------------------------------------------------------------------+
#   |  This page handler is called by graphs embedded in a dashboard.      |
#   '----------------------------------------------------------------------'


class PageGraphDashlet(cmk.gui.pages.Page):
    @classmethod
    def ident(cls) -> str:
        return "graph_dashlet"

    def page(self) -> cmk.gui.pages.PageResult:
        return host_service_graph_dashlet_cmk(
            parse_raw_graph_specification(json.loads(request.get_str_input_mandatory("spec"))),
            GraphRenderConfig.model_validate_json(request.get_str_input_mandatory("config")),
            graph_display_id=request.get_str_input_mandatory("id"),
        )
