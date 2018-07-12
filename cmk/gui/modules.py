#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2015             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# The official homepage is at http://mathias-kettner.de/check_mk.
#
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

import os
import sys
import importlib
from types import ModuleType

import cmk.paths

import cmk.gui.utils as utils
import cmk.gui.pagetypes as pagetypes

# Register non page specific modules which are not having own pages,
# but plugins to be loaded.
internal_module_names = [
    "cmk.gui.hooks",
    "cmk.gui.default_permissions",
    "cmk.gui.visuals"
]

import cmk
if not cmk.is_raw_edition():
    internal_module_names.append("cmk.gui.cee.sla")

pagehandlers = {}

# Modules to be loaded within the application by default. These
# modules are loaded on application initialization. The module
# function load_plugins() is called for all these modules to
# initialize them.
modules = []


# Returns a list of names of all currently imported python modules
def imports():
    for name, val in globals().items():
        if isinstance(val, ModuleType):
            yield val.__name__


def cleanup_already_imported_modules():
    g = globals()
    for module in modules:
        try:
            del g[module.__name__]
        except KeyError:
            pass # not loaded, it's ok


# Loads all modules needed into memory and performs global initializations for
# each module, when it needs some. These initializations should be fast ones.
# If you need more time cosuming initializations, they should be done in
# the late_init_modules() function.
def init_modules():
    global modules, pagehandlers

    cleanup_already_imported_modules()

    modules      = []
    pagehandlers = {}

    module_names_prev = set(imports())

    # The config module is handled separate from the other modules
    module_names_prev.add("cmk.gui.config")

    # Load the list of internal hard coded modules
    for module_name in internal_module_names:
        modules.append(importlib.import_module(module_name))

    # Load all multisite pages which will also perform imports of the needed modules
    utils.load_web_plugins('pages', globals())

    # Save the modules loaded during the former steps in the modules list
    modules += [ sys.modules[m] for m in set(imports()).difference(module_names_prev) ]


g_all_modules_loaded = False

# Call the load_plugins() function in all modules
def load_all_plugins():
    global g_all_modules_loaded

    # Optimization: in case of the graph ajax call only check the metrics module. This
    # improves the performance for these requests.
    # TODO: CLEANUP: Move this to the pagehandlers if this concept works out.
    if html.myfile == "ajax_graph" and g_all_modules_loaded:
        only_modules = ["metrics"]
    else:
        only_modules = None

    need_plugins_reload = _local_web_plugins_have_changed()

    for module in modules:
        if only_modules != None and module.__name__ not in only_modules:
            continue
        try:
            module.load_plugins # just check if this function exists
        except AttributeError:
            pass
        else:
            module.load_plugins(force = need_plugins_reload)

    # Install page handlers created by the pagetypes.py modules. It is allowed for all
    # kind of plugins to register own page types, so we need to wait after all plugins
    # have been loaded to update the pagehandlers
    register_handlers(pagetypes.page_handlers())

    # Mark the modules as loaded after all plugins have been loaded. In case of exceptions
    # we want them to occur again on subsequent requests too.
    g_all_modules_loaded = True


def register_handlers(handlers):
    pagehandlers.update(handlers)


def get_handler(name, dflt=None):
    return pagehandlers.get(name, dflt)


def _find_local_web_plugins():
    basedir = cmk.paths.local_web_dir + "/plugins/"

    try:
        plugin_dirs = os.listdir(basedir)
    except OSError, e:
        if e.errno == 2:
            return
        else:
            raise

    for plugins_dir in plugin_dirs:
        dir_path = basedir + plugins_dir
        yield dir_path # Changes in the directory like deletion of files!
        if os.path.isdir(dir_path):
            for file_name in os.listdir(dir_path):
                if file_name.endswith(".py") or file_name.endswith(".pyc"):
                    yield dir_path + "/" + file_name


_last_web_plugins_update = 0
def _local_web_plugins_have_changed():
    global _last_web_plugins_update

    if html.is_cached("local_web_plugins_have_changed"):
        return html.get_cached("local_web_plugins_have_changed")

    this_time = 0.0
    for path in _find_local_web_plugins():
        this_time = max(os.stat(path).st_mtime, this_time)
    last_time = _last_web_plugins_update
    _last_web_plugins_update = this_time

    have_changed = this_time > last_time
    html.set_cache("local_web_plugins_have_changed", have_changed)
    return have_changed
