#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.graphing_engine import ApiGraph, ApiPerfometer
from cmk.gui.log import logger

from ._from_api import graphs_from_api, perfometers_from_api
from ._plugins import graphing_plugins, GraphingPlugins


def _add_graphing_plugins(plugins: GraphingPlugins) -> None:
    for plugin in plugins.plugins.values():
        if isinstance(plugin, ApiPerfometer):
            perfometers_from_api.register(plugin)
        elif isinstance(plugin, ApiGraph):
            graphs_from_api.register(plugin)


def register_plugins() -> None:
    plugins = graphing_plugins()
    for exc in plugins.errors:
        logger.error(exc)
    _add_graphing_plugins(plugins)
