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
import math
import copy
import ast
from collections import OrderedDict

import cmk.paths
from cmk.exceptions import MKGeneralException

import cmk_base
import cmk_base.utils
import cmk_base.rulesets as rulesets
import cmk_base.config as config
import cmk_base.console as console
import cmk_base.check_api as check_api

# TODO: Cleanup access to check_info[] -> replace it by different function calls
# like for example check_exists(...)

_check_contexts                     = {} # The checks are loaded into this dictionary. Each check
                                        # becomes a separat sub-dictionary, named by the check name
_include_contexts                   = {} # These are the contexts of the check include files

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

# Names of variables registered in the check files. This is used to
# keep track of the variables needed by each file. Those variables are then
# (if available) read from the config and applied to the checks module after
# reading in the configuration of the user.
_check_variables                    = {}

# workaround: set of check-groups that are to be treated as service-checks even if
#   the item is None
service_rule_groups = set([
    "temperature"
])


#.
#   .--Loading-------------------------------------------------------------.
#   |                _                    _ _                              |
#   |               | |    ___   __ _  __| (_)_ __   __ _                  |
#   |               | |   / _ \ / _` |/ _` | | '_ \ / _` |                 |
#   |               | |__| (_) | (_| | (_| | | | | | (_| |                 |
#   |               |_____\___/ \__,_|\__,_|_|_| |_|\__, |                 |
#   |                                               |___/                  |
#   +----------------------------------------------------------------------+
#   | Loading of check plugins                                             |
#   '----------------------------------------------------------------------'

# Load all checks and includes
def load():
    filelist = get_plugin_paths(cmk.paths.local_checks_dir, cmk.paths.checks_dir)
    load_checks(filelist)


def get_plugin_paths(*dirs):
    filelist = []
    for dir in dirs:
        filelist += _plugin_pathnames_in_directory(dir)

    # read include files always first, but still in the sorted
    # order with local ones last (possibly overriding variables)
    return [ f for f in filelist if f.endswith(".include") ] + \
           [ f for f in filelist if not f.endswith(".include") ]


# Now read in all checks. Note: this is done *before* reading the
# configuration, because checks define variables with default
# values user can override those variables in his configuration.
# If a check or check.include is both found in local/ and in the
# normal structure, then only the file in local/ must be read!
def load_checks(filelist):
    loaded_files = set()
    check_variable_defaults = {}
    ignored_variable_types = [ type(lambda: None), type(os) ]
    for f in filelist:
        if f[0] == "." or f[-1] == "~":
            continue # ignore editor backup / temp files

        file_name  = os.path.basename(f)
        is_include = file_name.endswith(".include")
        if file_name in loaded_files:
            continue # skip already loaded files (e.g. from local)

        try:
            check_context = _new_check_context(f)

            known_vars = check_context.keys()
            known_checks = check_info.keys()

            execfile(f, check_context)
            loaded_files.add(file_name)

        except Exception, e:
            console.error("Error in plugin file %s: %s\n", f, e)
            if cmk.debug.enabled():
                raise
            else:
                continue

        new_checks = set(check_info.keys()).difference(known_checks)
        if is_include:
            _include_contexts[file_name] = check_context
        else:
            # Now store the check context for all checks found in this file
            for check_name in new_checks:
                _check_contexts[check_name] = check_context

        # Collect all variables that the check file did introduce compared to the
        # default check context
        new_check_vars = {}
        for varname in set(check_context.keys()).difference(known_vars):
            new_check_vars[varname] = check_context[varname]

        # The default_levels_variable of check_info also declares use of a global
        # variable. Register it here for this context.
        for check_name in new_checks:
            # The check_info is not converted yet (convert_check_info()). This means we need
            # to deal with old style tuple configured checks
            if type(check_info[check_name]) == tuple:
                default_levels_varname = check_default_levels.get(check_name)
            else:
                default_levels_varname = check_info[check_name].get("default_levels_variable")

            if default_levels_varname:
                new_check_vars[default_levels_varname] = \
                    factory_settings.get(default_levels_varname, {})

        # Save check variables for e.g. after config loading that the config can
        # be added to the check contexts
        for varname, value in new_check_vars.items():
            if varname[0] != '_' and type(value) not in ignored_variable_types:
                check_variable_defaults[varname] = value

                # Keep track of which variable needs to be set to which context
                context_ident_list = _check_variables.setdefault(varname, [])
                if is_include:
                    context_ident_list.append(file_name)
                else:
                    context_ident_list += new_checks

    # Hack to make dependencies between multiple includes work. In case we
    # need more here we need to find another solution.
    # TODO(lm): This needs to be cleaned up. Try to move the includes to
    # python modules that are separated from each other and can refer to
    # each other.
    _include_contexts["if64.include"].update(_include_contexts["if.include"])

    config.add_check_variables(check_variable_defaults)

    # Now convert check_info to new format.
    convert_check_info()
    verify_checkgroup_members()
    initialize_check_type_caches()


# Constructs a new check context dictionary. It contains the whole check API.
def _new_check_context(check_file_path):
    # Add the data structures where the checks register with Check_MK
    context = {
        "check_info"             : check_info,
        "check_includes"         : check_includes,
        "precompile_params"      : precompile_params,
        "check_default_levels"   : check_default_levels,
        "factory_settings"       : factory_settings,
        "check_config_variables" : check_config_variables,
        "snmp_info"              : snmp_info,
        "snmp_scan_functions"    : snmp_scan_functions,
        "active_check_info"      : active_check_info,
        "special_agent_info"     : special_agent_info,
    }

    # Add the Check API
    #
    # For better separation it would be better to copy the check API objects, but
    # this might consume too much memory. So we simply reference it.
    for k, v in check_api._get_check_context():
        context[k] = v

    # Load the definitions of the required include files for this check
    # Working with imports when specifying the includes would be much cleaner,
    # sure. But we need to deal with the current check API.
    if check_file_path and not check_file_path.endswith(".include"):
        for include_file_name in includes_of_plugin(check_file_path):
            try:
                context.update(_include_contexts[include_file_name])
            except KeyError, e:
                raise MKGeneralException("The include file %s does not exist" % include_file_name)

    return context


# Parse the check file without executing the code to find the check include
# files the check uses. The following statements are extracted:
# check_info[...] = { "includes": [...] }
# inv_info[...] = { "includes": [...] }
# check_includes[...] = [...]
def includes_of_plugin(check_file_path):
    include_names = OrderedDict()

    def _load_from_check_info(node):
        if not isinstance(node.value, ast.Dict):
            return

        for key, val in zip(node.value.keys, node.value.values):
            if key.s == "includes":
                if isinstance(val, ast.List):
                    for element in val.elts:
                        include_names[element.s] = True
                else:
                    raise MKGeneralException("Includes must be a list of include file names, "
                                             "found '%s'" % type(val))


    def _load_from_check_includes(node):
        if isinstance(node.value, ast.List):
            for element in node.value.elts:
                include_names[element.s] = True


    tree = ast.parse(open(check_file_path).read())
    for child in ast.iter_child_nodes(tree):
        if not isinstance(child, ast.Assign):
            continue # We only care about top level assigns

        # Filter out assignments to check_info dictionary
        for target in child.targets:
            if isinstance(target, ast.Subscript) and isinstance(target.value, ast.Name):
                if target.value.id in [ "check_info", "inv_info" ]:
                   _load_from_check_info(child)
                elif target.value.id == "check_includes":
                   _load_from_check_includes(child)

    return include_names.keys()


def _plugin_pathnames_in_directory(path):
    if path and os.path.exists(path):
        return sorted([
            path + "/" + f
            for f in os.listdir(path)
            if not f.startswith(".")
        ])
    else:
        return []


def check_variable_names():
    return _check_variables.keys()


def get_include_context(include_file_name):
    return _include_contexts[include_file_name]


# Some variables are accessed from the generic Check_MK code. E.g. during
# constructing the parameters of a check before executing the check function,
# or during loading of the configuration and the autochecks.
# Some variables are accessed by the discovery function during discovery.
# So store the variables in the global context of this module and the checks
# context.
# TODO: This could eventually be cleaned up when compute_check_parameters()
#       would use the checks context.
def set_check_variable(varname, value):
    globals()[varname] = value
    for context_ident in _check_variables[varname]:
        if context_ident.endswith(".include"):
            _include_contexts[context_ident][varname] = value
        else:
            _check_contexts[context_ident][varname] = value


# FIXME: Clear / unset all legacy variables to prevent confusions in other code trying to
# use the legacy variables which are not set by newer checks.
def convert_check_info():
    check_info_defaults = {
        "check_function"          : None,
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
            if inventory_function == check_api.no_discovery_possible:
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
                    raise MKGeneralException("Invalid check implementation: node_info for %s is "
                                             "True, but base check %s not defined" %
                                                (check_type, base_check))
            elif check_info[base_check]["node_info"] != info["node_info"]:
               raise MKGeneralException("Invalid check implementation: node_info for %s "
                                        "and %s are different." % ((base_check, check_type)))

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


# These caches both only hold the base names of the checks
def initialize_check_type_caches():
    snmp_cache = cmk_base.runtime_cache.get_set("check_type_snmp")
    snmp_cache.update(snmp_info.keys())

    tcp_cache = cmk_base.runtime_cache.get_set("check_type_tcp")
    for check_type, check in check_info.items():
        basename = check_type.split(".")[0]
        if basename not in snmp_cache:
            tcp_cache.add(basename)

#.
#   .--Helpers-------------------------------------------------------------.
#   |                  _   _      _                                        |
#   |                 | | | | ___| |_ __   ___ _ __ ___                    |
#   |                 | |_| |/ _ \ | '_ \ / _ \ '__/ __|                   |
#   |                 |  _  |  __/ | |_) |  __/ |  \__ \                   |
#   |                 |_| |_|\___|_| .__/ \___|_|  |___/                   |
#   |                              |_|                                     |
#   +----------------------------------------------------------------------+
#   | Misc check related helper functions                                  |
#   '----------------------------------------------------------------------'

def set_hostname(hostname):
    check_api._hostname = hostname


def set_service(check_type, descr):
    check_api._check_type          = check_type
    check_api._service_description = descr


# Remove illegal characters from a service description
def sanitize_service_description(descr):
    cache = cmk_base.config_cache.get_dict("sanitize_service_description")

    try:
        return cache[descr]
    except KeyError:
        new_descr = "".join([ c for c in descr
                             if c not in config.nagios_illegal_chars ]).rstrip("\\")
        cache[descr] = new_descr
        return new_descr


def is_snmp_check(check_name):
    cache = cmk_base.runtime_cache.get_dict("is_snmp_check")

    try:
        return cache[check_name]
    except KeyError:
        snmp_checks = cmk_base.runtime_cache.get_set("check_type_snmp")

        result = check_name.split(".")[0] in snmp_checks
        cache[check_name] = result
        return result


def is_tcp_check(check_name):
    cache = cmk_base.runtime_cache.get_dict("is_tcp_check")

    try:
        return cache[check_name]
    except KeyError:
        tcp_checks = cmk_base.runtime_cache.get_set("check_type_tcp")

        result = check_name.split(".")[0] in tcp_checks
        cache[check_name] = result
        return result


def discoverable_tcp_checks():
    types = []

    for check_type, check in check_info.items():
        if is_tcp_check(check_type) and check["inventory_function"]:
            types.append(check_type)

    return sorted(types)


# Compute parameters for a check honoring factory settings,
# default settings of user in main.mk, check_parameters[] and
# the values code in autochecks (given as parameter params)
def compute_check_parameters(host, checktype, item, params):
    if checktype not in check_info: # handle vanished checktype
        return None

    # Handle dictionary based checks
    def_levels_varname = check_info[checktype].get("default_levels_variable")
    # TODO: Can we skip this?
    #if def_levels_varname:
    #    vars_before_config.add(def_levels_varname)

    # Handle case where parameter is None but the type of the
    # default value is a dictionary. This is for example the
    # case if a check type has gotten parameters in a new version
    # but inventory of the old version left None as a parameter.
    # Also from now on we support that the inventory simply puts
    # None as a parameter. We convert that to an empty dictionary
    # that will be updated with the factory settings and default
    # levels, if possible.
    if params == None and def_levels_varname:
        fs = factory_settings.get(def_levels_varname)
        if type(fs) == dict:
            params = {}

    # Honor factory settings for dict-type checks. Merge
    # dict type checks with multiple matching rules
    if type(params) == dict:

        # Start with factory settings
        if def_levels_varname:
            new_params = factory_settings.get(def_levels_varname, {}).copy()
        else:
            new_params = {}

        # Merge user's default settings onto it
        if def_levels_varname and def_levels_varname in globals():
            def_levels = globals()[def_levels_varname]
            if type(def_levels) == dict:
                new_params.update(def_levels)

        # Merge params from inventory onto it
        new_params.update(params)
        params = new_params

    descr = config.service_description(host, checktype, item)

    # Get parameters configured via checkgroup_parameters
    entries = _get_checkgroup_parameters(host, checktype, item)

    # Get parameters configured via check_parameters
    entries += rulesets.service_extra_conf(host, descr, config.check_parameters)

    if entries:
        # loop from last to first (first must have precedence)
        for entry in entries[::-1]:
            if type(params) == dict and type(entry) == dict:
                params.update(entry)
            else:
                if type(entry) == dict:
                    # The entry still has the reference from the rule..
                    # If we don't make a deepcopy the rule might be modified by
                    # a followup params.update(...)
                    entry = copy.deepcopy(entry)
                params = entry
    return params


def _get_checkgroup_parameters(host, checktype, item):
    checkgroup = check_info[checktype]["group"]
    if not checkgroup:
        return []
    rules = config.checkgroup_parameters.get(checkgroup)
    if rules == None:
        return []

    try:
        # checks without an item
        if item == None and checkgroup not in service_rule_groups:
            return rulesets.host_extra_conf(host, rules)
        else: # checks with an item need service-specific rules
            return rulesets.service_extra_conf(host, item, rules)
    except MKGeneralException, e:
        raise MKGeneralException(str(e) + " (on host %s, checktype %s)" % (host, checktype))
