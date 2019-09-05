#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
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

import cmk.debug
import cmk.paths
from cmk.exceptions import MKGeneralException

import cmk_base.checks as checks
import cmk_base.check_api as check_api
import cmk_base.console as console
import cmk_base.inventory

# Inventory plugins have dependencies to check plugins and the inventory
# plugins need the check API. This is the easiest solution to get this
# working at the moment. In future some kind of OOP approach would be better.
# TODO: Clean this up!
#from cmk_base.checks import *

inv_info   = {} # Inventory plugins
inv_export = {} # Inventory export hooks
_plugin_contexts  = {} # The checks are loaded into this dictionary. Each check
                       # becomes a separat sub-dictionary, named by the check name
_include_contexts = {} # These are the contexts of the check include files


def load(): # pylint: disable=function-redefined
    loaded_files = set()
    filelist = checks.get_plugin_paths(cmk.paths.local_inventory_dir,
                                       cmk.paths.inventory_dir)

    for f in filelist:
        if f[0] == "." or f[-1] == "~":
            continue # ignore editor backup / temp files

        file_name  = os.path.basename(f)
        if file_name in loaded_files:
            continue # skip already loaded files (e.g. from local)

        try:
            plugin_context = _new_inv_context(f)
            known_plugins = inv_info.keys()

            load_plugin_includes(f, plugin_context)

            execfile(f, plugin_context)
            loaded_files.add(file_name)
        except Exception, e:
            console.error("Error in inventory plugin file %s: %s\n", f, e)
            if cmk.debug.enabled():
                raise
            else:
                continue

        # Now store the check context for all plugins found in this file
        for check_plugin_name in set(inv_info.keys()).difference(known_plugins):
            _plugin_contexts[check_plugin_name] = plugin_context


def _new_inv_context(plugin_file_path):
    # Add the data structures where the inventory plugins register with Check_MK
    context = {
        "inv_info"   : inv_info,
        "inv_export" : inv_export,
    }

    # Add the inventory plugin and check API
    #
    # For better separation it would be better to copy the check API objects, but
    # this might consume too much memory. So we simply reference it.
    for k, v in check_api._get_check_context() + _get_inventory_context():
        context[k] = v

    return context


# Load the definitions of the required include files for this check
# Working with imports when specifying the includes would be much cleaner,
# sure. But we need to deal with the current check API.
def load_plugin_includes(check_file_path, plugin_context):
    for include_file_name in checks.includes_of_plugin(check_file_path):
        include_file_path = os.path.join(cmk.paths.inventory_dir, include_file_name)

        local_path = os.path.join(cmk.paths.local_inventory_dir, include_file_name)
        if os.path.exists(local_path):
            include_file_path = local_path

        # inventory plugins may also use check includes. Try to find one.
        if not os.path.exists(include_file_path):
            include_file_path = checks.check_include_file_path(include_file_name)

            # In case a check include file is used the plugin context needs to be
            # prepared with a check plugin context
            for key, val in checks.new_check_context().items():
                plugin_context.setdefault(key, val)

        try:
            execfile(include_file_path, plugin_context)
        except Exception, e:
            console.error("Error in include file %s: %s\n", include_file_path, e)
            if cmk.debug.enabled():
                raise
            else:
                continue


def is_snmp_plugin(plugin_type):
    section_name = checks.section_name_of(plugin_type)
    return "snmp_info" in inv_info.get(section_name, {}) \
           or checks.is_snmp_check(plugin_type)

#.
#   .--Plugin API----------------------------------------------------------.
#   |           ____  _             _            _    ____ ___             |
#   |          |  _ \| |_   _  __ _(_)_ __      / \  |  _ \_ _|            |
#   |          | |_) | | | | |/ _` | | '_ \    / _ \ | |_) | |             |
#   |          |  __/| | |_| | (_| | | | | |  / ___ \|  __/| |             |
#   |          |_|   |_|\__,_|\__, |_|_| |_| /_/   \_\_|  |___|            |
#   |                         |___/                                        |
#   +----------------------------------------------------------------------+
#   | Helper API for being used in inventory plugins. Plugins have access  |
#   | to all things defined by the regular Check_MK check API and all the  |
#   | things declared here.                                                |
#   '----------------------------------------------------------------------'

def _get_inventory_context():
    return [
        ("inv_tree_list", cmk_base.inventory.inv_tree_list),
        ("inv_tree", cmk_base.inventory.inv_tree),
    ]


def sorted_inventory_plugins():

    # First resolve *all* dependencies. This ensures that there
    # are no cyclic dependencies, and that the 'depends on'
    # relation is transitive.
    resolved_dependencies = {}

    def resolve_plugin_dependencies(plugin_name, known_dependencies=None):
        '''recursively aggregate all plugin dependencies'''
        if known_dependencies is None:
            known_dependencies = set()
        if plugin_name in resolved_dependencies:
            known_dependencies.update(resolved_dependencies[plugin_name])
            return known_dependencies

        try:
            direct_dependencies = set(inv_info[plugin_name].get('depends_on', []))
        except KeyError:
            raise MKGeneralException("unknown plugin dependency: %r" % plugin_name)

        new_dependencies = direct_dependencies - known_dependencies
        known_dependencies.update(new_dependencies)
        for dependency in new_dependencies:
            known_dependencies = resolve_plugin_dependencies(dependency, known_dependencies)
        return known_dependencies

    for plugin_name in inv_info:
        resolved_dependencies[plugin_name] = resolve_plugin_dependencies(plugin_name)
        if plugin_name in resolved_dependencies[plugin_name]:
            raise MKGeneralException("cyclic plugin dependencies for %r" % plugin_name)

    # The plugins are now a partially ordered set with respect to
    # the 'depends on' relation. That means we can iteratively
    # yield the minimal elements
    remaining_plugins = set(inv_info.keys())
    yielded_plugins = set()
    while remaining_plugins:
        for plugin_name in sorted(remaining_plugins):
            dependencies = resolved_dependencies[plugin_name]
            if dependencies <= yielded_plugins:
                yield plugin_name, inv_info[plugin_name]
                yielded_plugins.add(plugin_name)
                remaining_plugins.remove(plugin_name)
