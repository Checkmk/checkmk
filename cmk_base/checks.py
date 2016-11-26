#!/usr/bin/env python
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
from cmk.exceptions import MKGeneralException

import cmk_base
import cmk_base.rulesets as rulesets
import cmk_base.config as config
import cmk_base.console as console
import cmk_base.snmp as snmp
import cmk_base.item_state as item_state

# TODO: Cleanup access to check_info[] -> replace it by different function calls
# like for example check_exists(...)

# The following data structures will be filled by the checks
check_info                         = {} # all known checks
check_includes                     = {} # library files needed by checks
precompile_params                  = {} # optional functions for parameter precompilation
check_default_levels               = {} # dictionary-configured checks declare their default level variables here
factory_settings                   = {} # factory settings for dictionary-configured checks
check_config_variables             = [] # variables (names) in checks/* needed for check itself
snmp_info                          = {} # whichs OIDs to fetch for which check (for tabular information)
snmp_scan_functions                = {} # SNMP autodetection
active_check_info                  = {} # definitions of active "legacy" checks
special_agent_info                 = {}

# Now read in all checks. Note: this is done *before* reading the
# configuration, because checks define variables with default
# values user can override those variables in his configuration.
# If a check or check.include is both found in local/ and in the
# normal structure, then only the file in local/ must be read!
def load():
    filelist = plugin_pathnames_in_directory(cmk.paths.local_checks_dir) \
             + plugin_pathnames_in_directory(cmk.paths.checks_dir)

    # read include files always first, but still in the sorted
    # order with local ones last (possibly overriding variables)
    filelist = [ f for f in filelist if f.endswith(".include") ] + \
               [ f for f in filelist if not f.endswith(".include") ]

    varname = None
    value = None
    ignored_variable_types = [ type(lambda: None), type(os) ]

    known_vars = set(globals().keys()) # track new configuration variables

    loaded_files = set()
    for f in filelist:
        if not f.endswith("~"): # ignore emacs-like backup files
            file_name = f.rsplit("/", 1)[-1]
            if file_name not in loaded_files:
                try:
                    loaded_files.add(file_name)
                    execfile(f, globals())
                except Exception, e:
                    console.error("Error in plugin file %s: %s\n", f, e)
                    if cmk.debug.enabled():
                        raise

    for varname, value in globals().iteritems():
        if varname[0] != '_' \
           and varname not in known_vars \
           and type(value) not in ignored_variable_types:
            config.register(varname, value)

    # Now convert check_info to new format.
    convert_check_info()
    verify_checkgroup_members()
    initialize_check_type_caches()


def plugin_pathnames_in_directory(path):
    if path and os.path.exists(path):
        return sorted([
            path + "/" + f
            for f in os.listdir(path)
            if not f.startswith(".")
        ])
    else:
        return []


# FIXME: Clear / unset all legacy variables to prevent confusions in other code trying to
# use the legacy variables which are not set by newer checks.
def convert_check_info():
    check_info_defaults = {
        "check_function"          : check_unimplemented,
        "inventory_function"      : None,
        "parse_function"          : None,
        "group"                   : None,
        "snmp_info"               : None,
        "snmp_scan_function"      : None,
        "handle_empty_info"       : False,
        "handle_real_time_checks" : False,
        "default_levels_variable" : None,
        "node_info"               : False,
        "extra_sections"          : [],
        "service_description"     : None,
        "has_perfdata"            : False,
    }

    for check_type, info in check_info.items():
        basename = check_type.split(".")[0]

        if type(info) != dict:
            # Convert check declaration from old style to new API
            check_function, service_description, has_perfdata, inventory_function = info
            if inventory_function == no_discovery_possible:
                inventory_function = None

            check_info[check_type] = {
                "check_function"          : check_function,
                "service_description"     : service_description,
                "has_perfdata"            : not not has_perfdata,
                "inventory_function"      : inventory_function,
                # Insert check name as group if no group is being defined
                "group"                   : check_type,
                "snmp_info"               : snmp_info.get(check_type),
                # Sometimes the scan function is assigned to the check_type
                # rather than to the base name.
                "snmp_scan_function"      :
                    snmp_scan_functions.get(check_type,
                        snmp_scan_functions.get(basename)),
                "handle_empty_info"       : False,
                "handle_real_time_checks" : False,
                "default_levels_variable" : check_default_levels.get(check_type),
                "node_info"               : False,
                "parse_function"          : None,
                "extra_sections"          : [],
            }
        else:
            # Ensure that there are only the known keys set. Is meant to detect typos etc.
            for key in info.keys():
                if key != "includes" and key not in check_info_defaults:
                    raise MKGeneralException("The check '%s' declares an unexpected key '%s' in 'check_info'." %
                                                                                    (check_type, key))

            # Check does already use new API. Make sure that all keys are present,
            # extra check-specific information into file-specific variables.
            for key, val in check_info_defaults.items():
                info.setdefault(key, val)

            # Include files are related to the check file (= the basename),
            # not to the (sub-)check. So we keep them in check_includes.
            check_includes.setdefault(basename, [])
            check_includes[basename] += info.get("includes", [])

    # Make sure that setting for node_info of check and subcheck matches
    for check_type, info in check_info.iteritems():
        if "." in check_type:
            base_check = check_type.split(".")[0]
            if base_check not in check_info:
                if info["node_info"]:
                    raise MKGeneralException("Invalid check implementation: node_info for %s is True, but base check %s not defined" %
                        (check_type, base_check))
            elif check_info[base_check]["node_info"] != info["node_info"]:
               raise MKGeneralException("Invalid check implementation: node_info for %s and %s are different." % (
                   (base_check, check_type)))

    # Now gather snmp_info and snmp_scan_function back to the
    # original arrays. Note: these information is tied to a "agent section",
    # not to a check. Several checks may use the same SNMP info and scan function.
    for check_type, info in check_info.iteritems():
        basename = check_type.split(".")[0]
        if info["snmp_info"] and basename not in snmp_info:
            snmp_info[basename] = info["snmp_info"]
        if info["snmp_scan_function"] and basename not in snmp_scan_functions:
            snmp_scan_functions[basename] = info["snmp_scan_function"]


# This function validates the checks which are members of checkgroups to have either
# all or none an item. Mixed checkgroups lead to strange exceptions when processing
# the check parameters. So it is much better to catch these errors in a central place
# with a clear error message.
def verify_checkgroup_members():
    groups = checks_by_checkgroup()

    for group_name, checks in groups.items():
        with_item, without_item = [], []
        for check_type, check in checks:
            # Trying to detect whether or not the check has an item. But this mechanism is not
            # 100% reliable since Check_MK appends an item to the service_description when "%s"
            # is not in the checks service_description template.
            # Maybe we need to define a new rule which enforces the developer to use the %s in
            # the service_description. At least for grouped checks.
            if "%s" in check["service_description"]:
                with_item.append(check_type)
            else:
                without_item.append(check_type)

        if with_item and without_item:
            raise MKGeneralException("Checkgroup %s has checks with and without item! At least one of "
                                     "the checks in this group needs to be changed (With item: %s, "
                                     "Without item: %s)" % (group_name, ", ".join(with_item), ", ".join(without_item)))


def checks_by_checkgroup():
    groups = {}
    for check_type, check in check_info.items():
        group_name = check["group"]
        if group_name:
            groups.setdefault(group_name, [])
            groups[group_name].append((check_type, check))
    return groups


def initialize_check_type_caches():
    snmp_cache = cmk_base.runtime_cache.get_set("check_type_snmp")
    snmp_cache.update(snmp_info.keys())

    tcp_cache = cmk_base.runtime_cache.get_set("check_type_tcp")
    tcp_cache.update(check_info.keys())


#.
#   .--Check API-----------------------------------------------------------.
#   |             ____ _               _         _    ____ ___             |
#   |            / ___| |__   ___  ___| | __    / \  |  _ \_ _|            |
#   |           | |   | '_ \ / _ \/ __| |/ /   / _ \ | |_) | |             |
#   |           | |___| | | |  __/ (__|   <   / ___ \|  __/| |             |
#   |            \____|_| |_|\___|\___|_|\_\ /_/   \_\_|  |___|            |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |  Helper API for being used in checks                                 |
#   '----------------------------------------------------------------------'
# TODO: Wrap everything in an API object

# TODO: Move imports directly to checks?
import re
import time
from cmk.regex import regex

BINARY     = snmp.BINARY
CACHED_OID = snmp.CACHED_OID

OID_END              = snmp.OID_END
OID_STRING           = snmp.OID_STRING
OID_BIN              = snmp.OID_BIN
OID_END_BIN          = snmp.OID_END_BIN
OID_END_OCTET_STRING = snmp.OID_END_OCTET_STRING


def saveint(i):
    try:
        return int(i)
    except:
        return 0


def savefloat(f):
    try:
        return float(f)
    except:
        return 0.0


# The function no_discovery_possible is as stub function used for
# those checks that do not support inventory. It must be known before
# we read in all the checks
def no_discovery_possible(check_type, info):
    console.verbose("%s does not support discovery. Skipping it.\n", check_type)
    return []

service_extra_conf     = rulesets.service_extra_conf
get_age_human_readable = cmk.render.approx_age

#
# Counter handling
#

set_item_state     = item_state.set_item_state
get_item_state     = item_state.get_item_state
clear_item_state   = item_state.clear_item_state
get_rate           = item_state.get_rate
get_average        = item_state.get_average
# TODO: Cleanup checks and deprecate this
last_counter_wrap  = item_state.last_counter_wrap

SKIP  = item_state.SKIP
RAISE = item_state.RAISE
ZERO  = item_state.ZERO

MKCounterWrapped = item_state.MKCounterWrapped
