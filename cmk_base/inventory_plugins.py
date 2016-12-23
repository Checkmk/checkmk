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

import cmk.paths

import cmk_base.checks as checks
import cmk_base.console as console
import cmk_base.inventory

# Inventory plugins have dependencies to check plugins and the inventory
# plugins need the check API. This is the easiest solution to get this
# working at the moment. In future some kind of OOP approach would be better.
from cmk_base.checks import *

inv_info = {}   # Inventory plugins
inv_export = {} # Inventory export hooks

def load(): # pylint: disable=function-redefined
    # Read all inventory plugins right now
    filelist = checks.plugin_pathnames_in_directory(cmk.paths.inventory_dir) \
             + checks.plugin_pathnames_in_directory(cmk.paths.local_inventory_dir)

    # read include files always first, but still in the sorted
    # order with local ones last (possibly overriding variables)
    filelist = [ f for f in filelist if f.endswith(".include") ] + \
               [ f for f in filelist if not f.endswith(".include") ]

    for f in filelist:
        if f.endswith("~"): # ignore emacs-like backup files
            continue

        try:
            execfile(f, globals(), globals())
        except Exception, e:
            console.error("Error in inventory plugin file %s: %s\n", f, e)
            if cmk.debug.enabled():
                raise
            sys.exit(5)


def is_snmp_plugin(plugin_type):
    info_type = plugin_type.split(".")[0]
    return "snmp_info" in inv_info.get(info_type, {})


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

inv_tree_list = cmk_base.inventory.inv_tree_list
inv_tree      = cmk_base.inventory.inv_tree
