#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import traceback
from contextlib import suppress
from pathlib import Path

from cmk import trace
from cmk.gui import (
    dashboard,
    graphing_main,
    hooks,
    utils,
    views,
    wato,
)
from cmk.gui.log import logger
from cmk.utils.plugin_loader import load_plugins_with_exceptions

tracer = trace.get_tracer()


@tracer.instrument("plugins.register")
def register() -> None:
    """Loads plugins"""
    _load_plugins("visuals")
    _load_plugins("sidebar")

    utils.load_web_plugins("pages", globals())

    hooks.unregister_plugin_hooks()

    views.register()
    _load_plugins("views")

    wato.register()
    with suppress(ModuleNotFoundError):
        # we don't ship this namespace anymore.
        # It's not clear to me if we have to support this for the `local` path
        _load_plugins("watolib")
    _load_plugins("wato")

    dashboard.register()
    _load_plugins("dashboard")

    graphing_main.register()


def _load_plugins(plugin_namespace: str) -> None:
    for plugin_name, exc in load_plugins_with_exceptions(f"cmk.gui.plugins.{plugin_namespace}"):
        logger.error("  Error in %s plug-in '%s'\n", plugin_namespace, plugin_name, exc_info=exc)
        utils.add_failed_plugin(
            Path(traceback.extract_tb(exc.__traceback__)[-1].filename),
            plugin_namespace,
            plugin_name,
            exc,
        )
