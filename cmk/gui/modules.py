#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# TODO: Cleanup this whole module.

# Once we drop the legacy plugin mechanism and changed the pages to be
# registered in a better way, for example using the standard plugin
# mechanism, we can change this to a module that is just importing
# all other "top level" modules of the application. e.g. like this:
#
# -> index.py
#  import cmk.gui.modules
#  -> modules.py
#      import cmk.gui.views
#      import cmk.gui.default_permissions
#      import ...
#
#      if not cmk_version.is_raw_edition():
#          import cmk.gui.cee.modules
#          -> cee/modules.py
#              import cmk.gui.cee.sla
#              import ...
#

import sys
from types import ModuleType
from typing import Any, Dict, Iterator, List

import cmk.utils.paths
import cmk.utils.version as cmk_version

import cmk.gui.pages
import cmk.gui.plugins.main_modules
import cmk.gui.utils as utils
from cmk.gui.log import logger

if not cmk_version.is_raw_edition():
    import cmk.gui.cee.plugins.main_modules  # pylint: disable=no-name-in-module

if cmk_version.is_managed_edition():
    import cmk.gui.cme.plugins.main_modules  # pylint: disable=no-name-in-module

# TODO: Both kept for compatibility with old plugins. Drop this one day
pagehandlers: Dict[Any, Any] = {}
# Modules to be loaded within the application by default. These
# modules are loaded on application initialization. The module
# function load_plugins() is called for all these modules to
# initialize them.
_legacy_modules: List[ModuleType] = []


def register_handlers(handlers: Dict) -> None:
    pagehandlers.update(handlers)


def _imports() -> Iterator[str]:
    """Returns a list of names of all currently imported python modules"""
    for val in globals().values():
        if isinstance(val, ModuleType):
            yield val.__name__


def init_modules() -> None:
    """Loads all modules needed into memory and performs global initializations for
    each module, when it needs some. These initializations should be fast ones."""
    global _legacy_modules

    _legacy_modules = []

    module_names_prev = set(_imports())

    # Load all multisite pages which will also perform imports of the needed modules
    utils.load_web_plugins("pages", globals())

    # Save the modules loaded during the former steps in the modules list
    _legacy_modules += [sys.modules[m] for m in set(_imports()).difference(module_names_prev)]


def call_load_plugins_hooks() -> None:
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

    for module in _cmk_gui_top_level_modules() + _legacy_modules:
        name = module.__name__

        if name == "cmk.gui.config":
            continue  # initial config is already loaded, nothing to do

        if not hasattr(module, "load_plugins"):
            continue  # has no load_plugins hook, nothing to do

        logger.debug("Executing load_plugins hook for %s", name)

        # hasattr above ensures the function is available. Mypy does not understand this.
        module.load_plugins()  # type: ignore[attr-defined]

    # TODO: Clean this up once we drop support for the legacy plugins
    for path, page_func in pagehandlers.items():
        cmk.gui.pages.register_page_handler(path, page_func)
    logger.debug("Finished executing load_plugin hooks")


def _cmk_gui_top_level_modules() -> List[ModuleType]:
    return [
        module  #
        for name, module in sys.modules.items()
        # None entries are only an import optimization of cPython and can be removed:
        # https://www.python.org/dev/peps/pep-0328/#relative-imports-and-indirection-entries-in-sys-modules
        if module is not None
        # top level modules only, please...
        if (
            name.startswith("cmk.gui.")
            and len(name.split(".")) == 3
            or name.startswith("cmk.gui.cee.")
            and len(name.split(".")) == 4
            or name.startswith("cmk.gui.cme.")
            and len(name.split(".")) == 4
        )
    ]
