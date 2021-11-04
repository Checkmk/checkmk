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

import errno
import os
import sys
from types import ModuleType
from typing import Any, Dict, Iterator, List, Set

import cmk.utils.paths
import cmk.utils.version as cmk_version

import cmk.gui.pages
import cmk.gui.plugins.main_modules
import cmk.gui.utils as utils
from cmk.gui.hooks import request_memoize
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

_plugins_loaded_for: Set[str] = set()


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

    Up to now this is executed during request processing. Like this:

    1. During the first request in an just initialized interpreter the `load_plugins()` is
       called.
    2. The main module is doing it's initialization logic.
    3. Some of the main modules then remember that they have loaded all plugins with a
       `loaded_with_language` variable.
    4. On subsequent requests the `load_plugins()` is executed and most main modules
       immaculately return without performing another action.
    5. Once any "local plugin" file has been modified (changed mtime), the all main modules are
       called with `load_plugins()` to perform their initialization again.

    This is done to automatically load/reload plugins after e.g. an MKP installation.

    Note: Might be better to trigger our application in case something is changed to do a restart
          from an external source like the MKP manager. In the moment we move the local plugins
          to regulary modules this will be required anyways.
    """
    logger.debug("Executing load_plugin hooks")

    if _local_web_plugins_have_changed():
        logger.debug("A local GUI plugin has changed. Enforcing execution of all hooks")
        _plugins_loaded_for.clear()

    for module in _cmk_gui_top_level_modules() + _legacy_modules:
        name = module.__name__

        if name == "cmk.gui.config":
            continue  # initial config is already loaded, nothing to do

        if not hasattr(module, "load_plugins"):
            continue  # has no load_plugins hook, nothing to do

        if name in _plugins_loaded_for:
            continue  # already loaded, nothing to do

        logger.debug("Executing load_plugins hook for %s", name)

        # hasattr above ensures the function is available. Mypy does not understand this.
        module.load_plugins()  # type: ignore[attr-defined]

        _plugins_loaded_for.add(name)

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


def _find_local_web_plugins() -> Iterator[str]:
    basedir = str(cmk.utils.paths.local_web_dir) + "/plugins/"

    try:
        plugin_dirs = os.listdir(basedir)
    except OSError as e:
        if e.errno == errno.ENOENT:
            return
        raise

    for plugins_dir in plugin_dirs:
        dir_path = basedir + plugins_dir
        yield dir_path  # Changes in the directory like deletion of files!
        if os.path.isdir(dir_path):
            for file_name in os.listdir(dir_path):
                if file_name.endswith(".py") or file_name.endswith(".pyc"):
                    yield dir_path + "/" + file_name


_last_web_plugins_update = 0.0


@request_memoize()
def _local_web_plugins_have_changed() -> bool:
    global _last_web_plugins_update

    this_time = 0.0
    for path in _find_local_web_plugins():
        this_time = max(os.stat(path).st_mtime, this_time)
    last_time = _last_web_plugins_update
    _last_web_plugins_update = this_time
    return this_time > last_time
