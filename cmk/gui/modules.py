#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
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
from typing import Optional, Iterator, Any, Dict, List

import cmk.utils.version as cmk_version
import cmk.utils.paths

import cmk.gui.utils as utils
import cmk.gui.pages
from cmk.gui.globals import g

import cmk.gui.plugins.main_modules

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
    utils.load_web_plugins('pages', globals())

    # Save the modules loaded during the former steps in the modules list
    _legacy_modules += [sys.modules[m] for m in set(_imports()).difference(module_names_prev)]


g_all_modules_loaded = False


def load_all_plugins(only_modules: Optional[List[str]] = None) -> None:
    """Call the load_plugins() function in all modules"""
    global g_all_modules_loaded
    # Initially, we have to load all modules, regardless of any optimization.
    if not g_all_modules_loaded:
        only_modules = None

    need_plugins_reload = _local_web_plugins_have_changed()

    for module in _cmk_gui_top_level_modules() + _legacy_modules:
        # initial config is already loaded, do not load it again
        if module.__name__ == "cmk.gui.config":
            continue
        if (only_modules is None or module.__name__ in only_modules) and \
           hasattr(module, "load_plugins"):
            # hasattr above ensures the function is available. Mypy does not understand this.
            module.load_plugins(force=need_plugins_reload)  # type: ignore[attr-defined]

    # TODO: Clean this up once we drop support for the legacy plugins
    for path, page_func in pagehandlers.items():
        cmk.gui.pages.register_page_handler(path, page_func)

    # Mark the modules as loaded after all plugins have been loaded. In case of exceptions
    # we want them to occur again on subsequent requests too.
    g_all_modules_loaded = True


def _cmk_gui_top_level_modules() -> List[ModuleType]:
    return [
        module  #
        for name, module in sys.modules.items()
        # None entries are only an import optimization of cPython and can be removed:
        # https://www.python.org/dev/peps/pep-0328/#relative-imports-and-indirection-entries-in-sys-modules
        if module is not None
        # top level modules only, please...
        if (name.startswith("cmk.gui.") and len(name.split(".")) == 3 or
            name.startswith("cmk.gui.cee.") and len(name.split(".")) == 4 or
            name.startswith("cmk.gui.cme.") and len(name.split(".")) == 4)
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


def _local_web_plugins_have_changed() -> bool:
    global _last_web_plugins_update

    if 'local_web_plugins_have_changed' in g:
        return g.local_web_plugins_have_changed

    this_time = 0.0
    for path in _find_local_web_plugins():
        this_time = max(os.stat(path).st_mtime, this_time)
    last_time = _last_web_plugins_update
    _last_web_plugins_update = this_time

    have_changed = this_time > last_time
    g.local_web_plugins_have_changed = have_changed
    return have_changed
