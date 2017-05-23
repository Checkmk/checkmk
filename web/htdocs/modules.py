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
from types import ModuleType
from lib import load_web_plugins, local_web_plugins_have_changed
from mod_python.apache import import_module
import pagetypes

# Register non page specific modules which are not having own pages,
# but plugins to be loaded.
internal_module_names = [
    'hooks',
    'default_permissions',
]

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
            yield get_module_name(val)


def cleanup_already_imported_modules():
    g = globals()
    for module in modules:
        try:
            del g[get_module_name(module)]
        except KeyError:
            pass # not loaded, it's ok


# module name can not be get from __name__ in mod_python. use the file path to detect it.
def get_module_name(module):
    return os.path.splitext(os.path.basename(module.__file__))[0]


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
    module_names_prev.add("config")

    # Load the list of internal hard coded modules
    for module_name in internal_module_names:
        # TODO: use __import__
        modules.append(import_module(module_name))

    # Load all multisite pages which will also perform imports of the needed modules
    load_web_plugins('pages', globals())

    # Save the modules loaded during the former steps in the modules list
    modules += [ globals()[m] for m in set(imports()).difference(module_names_prev) ]


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

    need_plugins_reload = local_web_plugins_have_changed()

    for module in modules:
        if only_modules != None and get_module_name(module) not in only_modules:
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
    pagehandlers.update(pagetypes.page_handlers())

    # Mark the modules as loaded after all plugins have been loaded. In case of exceptions
    # we want them to occur again on subsequent requests too.
    g_all_modules_loaded = True


def get_handler(name, dflt=None):
    return pagehandlers.get(name, dflt)
