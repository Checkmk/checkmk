#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import importlib
import traceback
from pathlib import Path
from types import ModuleType

from cmk import trace
from cmk.gui import (
    dashboard,
    graphing_main,
    hooks,
    notifications,
    pages,
    sidebar,
    userdb,
    utils,
    views,
    visuals,
    wato,
    watolib,
)
from cmk.gui.log import logger
from cmk.utils.plugin_loader import load_plugins_with_exceptions

tracer = trace.get_tracer()


@tracer.instrument("plugins.register")
def register() -> None:
    _import_main_module_plugins(
        [
            watolib,
            userdb,
            visuals,
            views,
            wato,
            dashboard,
            sidebar,
            pages,
        ]
    )
    utils.load_web_plugins("pages", globals())
    _call_load_plugins_hooks(
        [
            hooks,
            userdb,
            visuals,
            views,
            wato,
            dashboard,
            sidebar,
            graphing_main,
            notifications,
        ]
    )


def _import_main_module_plugins(main_modules: list[ModuleType]) -> None:
    logger.debug("Importing main module plugins")

    for module in main_modules:
        main_module_name = module.__name__.split(".")[-1]

        plugin_package_name = f"cmk.gui.plugins.{main_module_name}"
        if not _is_plugin_namespace(plugin_package_name):
            continue

        logger.debug("  Importing plug-ins from %s", plugin_package_name)
        for plugin_name, exc in load_plugins_with_exceptions(plugin_package_name):
            logger.error(
                "  Error in %s plug-in '%s'\n", main_module_name, plugin_name, exc_info=exc
            )
            utils.add_failed_plugin(
                Path(traceback.extract_tb(exc.__traceback__)[-1].filename),
                main_module_name,
                plugin_name,
                exc,
            )

    logger.debug("Main module plug-ins imported")


def _is_plugin_namespace(plugin_package_name: str) -> bool:
    # TODO: We should know this somehow by declarations without need to try this out
    try:
        importlib.import_module(plugin_package_name)
        return True
    except ModuleNotFoundError:
        return False


def _call_load_plugins_hooks(main_modules: list[ModuleType]) -> None:
    """Call the load_plugins() function in all main modules

    Have a look at our Wiki: /books/concepts/page/how-cmkgui-is-organised

    Each main module has the option to declare a `load_plugins` hook function to realize it's own
    logic that should be executed when initializing the main module.

    In previous versions this was executed with loaded configuration and localized during request
    processing, which resulted in several problems. Now this is executed during application
    initialization (at import time).

    1. During import of the application (e.g. web/app/index.wsgi) `init_modules` cares for the
       import of all main modules
    2. Then this function calls the function `load_plugins` hook of all main modules.
    3. The main module is doing it's initialization logic.
    """
    logger.debug("Executing load_plugin hooks")

    for module in main_modules:
        name = module.__name__

        if name == "cmk.gui.main_modules":
            continue  # Do not call ourselfs

        if not hasattr(module, "load_plugins"):
            continue  # has no load_plugins hook, nothing to do

        logger.debug("Executing load_plugins hook for %s", name)
        module.load_plugins()

    logger.debug("Finished executing load_plugin hooks")
