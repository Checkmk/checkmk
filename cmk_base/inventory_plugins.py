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

import cmk.paths

import cmk_base.config as config
import cmk_base.console as console
import cmk_base.check_utils

# Inventory plugins have dependencies to check plugins and the inventory
# plugins need the check API. This is the easiest solution to get this
# working at the moment. In future some kind of OOP approach would be better.
# TODO: Clean this up!
#from cmk_base.config import *

inv_info = {}  # Inventory plugins
inv_export = {}  # Inventory export hooks
_plugin_contexts = {}  # The checks are loaded into this dictionary. Each check
# becomes a separat sub-dictionary, named by the check name
_include_contexts = {}  # These are the contexts of the check include files


def load_plugins(get_check_api_context, get_inventory_context):
    loaded_files = set()
    filelist = config.get_plugin_paths(cmk.paths.local_inventory_dir, cmk.paths.inventory_dir)

    for f in filelist:
        if f[0] == "." or f[-1] == "~":
            continue  # ignore editor backup / temp files

        file_name = os.path.basename(f)
        if file_name in loaded_files:
            continue  # skip already loaded files (e.g. from local)

        try:
            plugin_context = _new_inv_context(get_check_api_context, get_inventory_context)
            known_plugins = inv_info.keys()

            _load_plugin_includes(f, plugin_context)

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


def _new_inv_context(get_check_api_context, get_inventory_context):
    # Add the data structures where the inventory plugins register with Check_MK
    context = {
        "inv_info": inv_info,
        "inv_export": inv_export,
    }
    # NOTE: For better separation it would be better to copy the values, but
    # this might consume too much memory, so we simply reference them.
    # NOTE: It is possible that check includes are included, so we need the
    # usual check context here, too.
    context.update(config.new_check_context(get_check_api_context))
    context.update(get_inventory_context())
    return context


# Load the definitions of the required include files for this check
# Working with imports when specifying the includes would be much cleaner,
# sure. But we need to deal with the current check API.
def _load_plugin_includes(check_file_path, plugin_context):
    for name in config.includes_of_plugin(check_file_path):
        path = _include_file_path(name)
        try:
            execfile(path, plugin_context)
        except Exception, e:
            console.error("Error in include file %s: %s\n", path, e)
            if cmk.debug.enabled():
                raise


def _include_file_path(name):
    local_path = os.path.join(cmk.paths.local_inventory_dir, name)
    if os.path.exists(local_path):
        return local_path
    shared_path = os.path.join(cmk.paths.inventory_dir, name)
    if os.path.exists(shared_path):
        return shared_path
    return config.check_include_file_path(name)


def is_snmp_plugin(plugin_type):
    section_name = cmk_base.check_utils.section_name_of(plugin_type)
    return "snmp_info" in inv_info.get(section_name, {}) \
           or cmk_base.check_utils.is_snmp_check(plugin_type)
