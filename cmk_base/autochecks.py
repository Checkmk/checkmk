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
import sys

import cmk.debug
import cmk.exceptions
import cmk.paths

import cmk_base.config
import cmk_base.console


# Read automatically discovered checks of one host.
# world: "config" -> File in var/check_mk/autochecks
#        "active" -> Copy in var/check_mk/core/autochecks
# Returns a table with three columns:
# 1. check_plugin_name
# 2. item
# 3. parameters evaluated!
# TODO: use store.load_data_from_file()
# TODO: Common code with parse_autochecks_file? Cleanup.
def read_autochecks_of(hostname, world="config"):
    if world == "config":
        basedir = cmk.paths.autochecks_dir
    else:
        basedir = cmk.paths.var_dir + "/core/autochecks"
    filepath = basedir + '/' + hostname + '.mk'

    if not os.path.exists(filepath):
        return []

    check_config = cmk_base.config.get_check_variables()
    try:
        autochecks_raw = eval(file(filepath).read(), check_config, check_config)
    except SyntaxError, e:
        cmk_base.console.verbose("Syntax error in file %s: %s\n", filepath, e, stream=sys.stderr)
        if cmk.debug.enabled():
            raise
        return []
    except Exception, e:
        cmk_base.console.verbose("Error in file %s:\n%s\n", filepath, e, stream=sys.stderr)
        if cmk.debug.enabled():
            raise
        return []

    # Exchange inventorized check parameters with those configured by
    # the user. Also merge with default levels for modern dictionary based checks.
    autochecks = []
    for entry in autochecks_raw:
        if len(entry) == 4:  # old format where hostname is at the first place
            entry = entry[1:]
        check_plugin_name, item, parameters = entry

        # With Check_MK 1.2.7i3 items are now defined to be unicode strings. Convert
        # items from existing autocheck files for compatibility. TODO remove this one day
        if isinstance(item, str):
            item = cmk_base.config.decode_incoming_string(item)

        if type(check_plugin_name) not in (str, unicode):
            raise cmk.exceptions.MKGeneralException(
                "Invalid entry '%r' in check table of host '%s': "
                "The check type must be a string." % (entry, hostname))

        autochecks.append((check_plugin_name, item,
                           cmk_base.config.compute_check_parameters(hostname, check_plugin_name,
                                                                    item, parameters)))
    return autochecks
