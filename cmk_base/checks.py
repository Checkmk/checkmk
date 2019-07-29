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
import marshal
import py_compile
import struct
from collections import OrderedDict

import cmk.paths
import cmk.store as store
from cmk.exceptions import MKGeneralException, MKTerminate

import cmk_base
import cmk_base.utils
import cmk_base.rulesets as rulesets
import cmk_base.config as config
import cmk_base.console as console
import cmk_base.check_api as check_api

# TODO: Cleanup access to check_info[] -> replace it by different function calls
# like for example check_exists(...)

# BE AWARE: sync these global data structures with
#           _initialize_data_structures()
# TODO: Refactor this.

_check_contexts                     = {} # The checks are loaded into this dictionary. Each check
                                         # has a separate sub-dictionary, named by the check name.
                                         # It is populated with the includes and the check itself.

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
# keeps the default values of all the check variables
_check_variable_defaults            = {}
_all_checks_loaded                  = False

# workaround: set of check-groups that are to be treated as service-checks even if
#   the item is None
service_rule_groups = set([
    "temperature"
])

class TimespecificParamList(list):
    pass


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

def load():
    """Load all checks and includes"""
    global _all_checks_loaded

    _initialize_data_structures()
    filelist = get_plugin_paths(cmk.paths.local_checks_dir, cmk.paths.checks_dir)
    load_checks(filelist)

    _all_checks_loaded = True


def _initialize_data_structures():
    """Initialize some data structures which are populated while loading the checks"""
    global _all_checks_loaded
    _all_checks_loaded = False

    _check_variables.clear()
    _check_variable_defaults.clear()

    _check_contexts.clear()
    check_info.clear()
    check_includes.clear()
    precompile_params.clear()
    check_default_levels.clear()
    factory_settings.clear()
    del check_config_variables[:]
    snmp_info.clear()
    snmp_scan_functions.clear()
    active_check_info.clear()
    special_agent_info.clear()


def get_plugin_paths(*dirs):
    filelist = []
    for dir in dirs:
        filelist += _plugin_pathnames_in_directory(dir)
    return filelist


# Now read in all checks. Note: this is done *before* reading the
# configuration, because checks define variables with default
# values user can override those variables in his configuration.
# If a check or check.include is both found in local/ and in the
# normal structure, then only the file in local/ must be read!
def load_checks(filelist):
    cmk_global_vars = set(config.get_variable_names())

    loaded_files = set()
    ignored_variable_types = [ type(lambda: None), type(os) ]
    for f in filelist:
        if f[0] == "." or f[-1] == "~":
            continue # ignore editor backup / temp files

        file_name  = os.path.basename(f)
        if file_name in loaded_files:
            continue # skip already loaded files (e.g. from local)

        try:
            check_context = new_check_context()

            known_vars = check_context.keys()
            known_checks = check_info.keys()
            known_active_checks = active_check_info.keys()

            load_check_includes(f, check_context)

            load_precompiled_plugin(f, check_context)
            loaded_files.add(file_name)

        except MKTerminate:
            raise

        except Exception, e:
            console.error("Error in plugin file %s: %s\n", f, e)
            if cmk.debug.enabled():
                raise
            else:
                continue

        new_checks = set(check_info.keys()).difference(known_checks)
        new_active_checks = set(active_check_info.keys()).difference(known_active_checks)

        # Now store the check context for all checks found in this file
        for check_plugin_name in new_checks:
            _check_contexts[check_plugin_name] = check_context

        for check_plugin_name in new_active_checks:
            _check_contexts[check_plugin_name] = check_context

        # Collect all variables that the check file did introduce compared to the
        # default check context
        new_check_vars = {}
        for varname in set(check_context.keys()).difference(known_vars):
            new_check_vars[varname] = check_context[varname]

        # The default_levels_variable of check_info also declares use of a global
        # variable. Register it here for this context.
        for check_plugin_name in new_checks:
            # The check_info is not converted yet (convert_check_info()). This means we need
            # to deal with old style tuple configured checks
            if type(check_info[check_plugin_name]) == tuple:
                default_levels_varname = check_default_levels.get(check_plugin_name)
            else:
                default_levels_varname = check_info[check_plugin_name].get("default_levels_variable")

            if default_levels_varname:
                # Add the initial configuration to the check context to have a consistent state
                check_context[default_levels_varname] = factory_settings.get(default_levels_varname, {})
                new_check_vars[default_levels_varname] = check_context[default_levels_varname]

        # Save check variables for e.g. after config loading that the config can
        # be added to the check contexts
        for varname, value in new_check_vars.items():
            # Do not allow checks to override Check_MK builtin global variables. Silently
            # skip them here. The variables will only be locally available to the checks.
            if varname in cmk_global_vars:
                continue

            if varname[0] != '_' and type(value) not in ignored_variable_types:
                _check_variable_defaults[varname] = value

                # Keep track of which variable needs to be set to which context
                context_ident_list = _check_variables.setdefault(varname, [])
                context_ident_list += new_checks
                context_ident_list += new_active_checks

    # Now convert check_info to new format.
    convert_check_info()
    verify_checkgroup_members()
    initialize_check_type_caches()


def all_checks_loaded():
    """Whether or not all(!) checks have been loaded into the current process"""
    return _all_checks_loaded


def any_check_loaded():
    """Whether or not some checks have been loaded into the current process"""
    return bool(_check_contexts)


# Constructs a new check context dictionary. It contains the whole check API.
def new_check_context():
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

    return context


# Load the definitions of the required include files for this check
# Working with imports when specifying the includes would be much cleaner,
# sure. But we need to deal with the current check API.
def load_check_includes(check_file_path, check_context):
    for include_file_name in cached_includes_of_plugin(check_file_path):
        include_file_path = check_include_file_path(include_file_name)
        try:
            load_precompiled_plugin(include_file_path, check_context)
        except MKTerminate:
            raise

        except Exception, e:
            console.error("Error in check include file %s: %s\n", include_file_path, e)
            if cmk.debug.enabled():
                raise
            else:
                continue


def check_include_file_path(include_file_name):
    include_file_path = os.path.join(cmk.paths.checks_dir, include_file_name)

    local_path = os.path.join(cmk.paths.local_checks_dir, include_file_name)
    if os.path.exists(local_path):
        include_file_path = local_path

    return include_file_path


def cached_includes_of_plugin(check_file_path):
    cache_file_path = _include_cache_file_path(check_file_path)
    try:
        return _get_cached_check_includes(check_file_path, cache_file_path)
    except OSError, e:
        pass # No usable cache. Terminate

    includes = includes_of_plugin(check_file_path)
    _write_check_include_cache(cache_file_path, includes)
    return includes


def _get_cached_check_includes(check_file_path, cache_file_path):
    check_stat = os.stat(check_file_path)
    cache_stat = os.stat(cache_file_path)

    if check_stat.st_mtime >= cache_stat.st_mtime:
        raise OSError("Cache is too old")

    # There are no includes (just the newline at the end)
    if cache_stat.st_size == 1:
        return [] # No includes

    # store.save_file() creates file empty for locking (in case it does not exists).
    # Skip loading the file.
    # Note: When raising here this process will also write the file. This means it
    # will write it another time after it was written by the other process. This
    # could be optimized. Since the whole caching here is a temporary(tm) soltion,
    # we leave it as it is.
    if cache_stat.st_size == 0:
        raise OSError("Cache generation in progress (file is locked)")

    x = open(cache_file_path).read().strip()
    if not x:
        return [] # Shouldn't happen. Empty files are handled above
    return x.split("|")


def _write_check_include_cache(cache_file_path, includes):
    store.makedirs(os.path.dirname(cache_file_path))
    store.save_file(cache_file_path, "%s\n" % "|".join(includes))


def _include_cache_file_path(path):
    is_local = path.startswith(cmk.paths.local_checks_dir)
    return os.path.join(cmk.paths.include_cache_dir,
                        "local" if is_local else "builtin",
                        os.path.basename(path))


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
            if not f.startswith(".") and not f.endswith(".include")
        ])
    else:
        return []


def load_precompiled_plugin(path, check_context):
    """Loads the given check or check include plugin into the given
    check context.

    To improve loading speed the files are not read directly. The files are
    python byte-code compiled before in case it has not been done before. In
    case there is already a compiled file that is newer than the current one,
    then the precompiled file is loaded."""

    precompiled_path = _precompiled_plugin_path(path)

    if not _is_plugin_precompiled(path, precompiled_path):
        console.vverbose("Precompile %s to %s\n" % (path, precompiled_path))
        store.makedirs(os.path.dirname(precompiled_path))
        py_compile.compile(path, precompiled_path, doraise=True)

    exec(marshal.loads(open(precompiled_path, "rb").read()[8:]), check_context)


def _is_plugin_precompiled(path, precompiled_path):
    if not os.path.exists(precompiled_path):
        return False

    # Check precompiled file header
    f = open(precompiled_path, "rb")

    file_magic = f.read(4)
    if file_magic != py_compile.MAGIC:
        return False

    try:
        origin_file_mtime = struct.unpack("I", f.read(4))[0]
    except struct.error, e:
        return False

    if long(os.stat(path).st_mtime) != origin_file_mtime:
        return False

    return True


def _precompiled_plugin_path(path):
    is_local = path.startswith(cmk.paths.local_checks_dir)
    return os.path.join(cmk.paths.precompiled_checks_dir,
                        "local" if is_local else "builtin",
                        os.path.basename(path))


def check_variable_names():
    return _check_variables.keys()


def get_check_variable_defaults():
    """Returns the check variable default settings. These are the settings right
    after loading the checks."""
    return _check_variable_defaults


def set_check_variables(check_variables):
    """Update the check related config variables in the relevant check contexts"""
    for varname, value in check_variables.items():
        for context_ident in _check_variables[varname]:
            _check_contexts[context_ident][varname] = value


def get_check_variables():
    """Returns the currently effective check variable settings

    Since the variables are only stored in the individual check contexts and not stored
    in a central place, this function needs to collect the values from the check contexts.
    We assume a single variable has the same value in all relevant contexts, which means
    that it is enough to get the variable from the first context."""
    check_config = {}
    for varname, context_ident_list in _check_variables.items():
        check_config[varname] = _check_contexts[context_ident_list[0]][varname]
    return check_config


def get_check_context(check_plugin_name):
    """Returns the context dictionary of the given check plugin"""
    return _check_contexts[check_plugin_name]


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
        "management_board"        : None,
    }

    for check_plugin_name, info in check_info.items():
        section_name = section_name_of(check_plugin_name)

        if type(info) != dict:
            # Convert check declaration from old style to new API
            check_function, service_description, has_perfdata, inventory_function = info
            if inventory_function == check_api.no_discovery_possible:
                inventory_function = None

            check_info[check_plugin_name] = {
                "check_function"          : check_function,
                "service_description"     : service_description,
                "has_perfdata"            : not not has_perfdata,
                "inventory_function"      : inventory_function,
                # Insert check name as group if no group is being defined
                "group"                   : check_plugin_name,
                "snmp_info"               : snmp_info.get(check_plugin_name),
                # Sometimes the scan function is assigned to the check_plugin_name
                # rather than to the base name.
                "snmp_scan_function"      :
                    snmp_scan_functions.get(check_plugin_name,
                        snmp_scan_functions.get(section_name)),
                "handle_empty_info"       : False,
                "handle_real_time_checks" : False,
                "default_levels_variable" : check_default_levels.get(check_plugin_name),
                "node_info"               : False,
                "parse_function"          : None,
                "extra_sections"          : [],
                "management_board"        : None,
            }
        else:
            # Ensure that there are only the known keys set. Is meant to detect typos etc.
            for key in info.keys():
                if key != "includes" and key not in check_info_defaults:
                    raise MKGeneralException("The check '%s' declares an unexpected key '%s' in 'check_info'." %
                                                                                    (check_plugin_name, key))

            # Check does already use new API. Make sure that all keys are present,
            # extra check-specific information into file-specific variables.
            for key, val in check_info_defaults.items():
                info.setdefault(key, val)

            # Include files are related to the check file (= the section_name),
            # not to the (sub-)check. So we keep them in check_includes.
            check_includes.setdefault(section_name, [])
            check_includes[section_name] += info.get("includes", [])

    # Make sure that setting for node_info of check and subcheck matches
    for check_plugin_name, info in check_info.iteritems():
        if "." in check_plugin_name:
            section_name = section_name_of(check_plugin_name)
            if section_name not in check_info:
                if info["node_info"]:
                    raise MKGeneralException("Invalid check implementation: node_info for %s is "
                                             "True, but base check %s not defined" %
                                                (check_plugin_name, section_name))

            elif check_info[section_name]["node_info"] != info["node_info"]:
               raise MKGeneralException("Invalid check implementation: node_info for %s "
                                        "and %s are different." % ((section_name, check_plugin_name)))

    # Now gather snmp_info and snmp_scan_function back to the
    # original arrays. Note: these information is tied to a "agent section",
    # not to a check. Several checks may use the same SNMP info and scan function.
    for check_plugin_name, info in check_info.iteritems():
        section_name = section_name_of(check_plugin_name)
        if info["snmp_info"] and section_name not in snmp_info:
            snmp_info[section_name] = info["snmp_info"]

        if info["snmp_scan_function"] and section_name not in snmp_scan_functions:
            snmp_scan_functions[section_name] = info["snmp_scan_function"]


# This function validates the checks which are members of checkgroups to have either
# all or none an item. Mixed checkgroups lead to strange exceptions when processing
# the check parameters. So it is much better to catch these errors in a central place
# with a clear error message.
def verify_checkgroup_members():
    groups = checks_by_checkgroup()

    for group_name, checks in groups.items():
        with_item, without_item = [], []
        for check_plugin_name, check in checks:
            # Trying to detect whether or not the check has an item. But this mechanism is not
            # 100% reliable since Check_MK appends an item to the service_description when "%s"
            # is not in the checks service_description template.
            # Maybe we need to define a new rule which enforces the developer to use the %s in
            # the service_description. At least for grouped checks.
            if "%s" in check["service_description"]:
                with_item.append(check_plugin_name)
            else:
                without_item.append(check_plugin_name)

        if with_item and without_item:
            raise MKGeneralException("Checkgroup %s has checks with and without item! At least one of "
                                     "the checks in this group needs to be changed (With item: %s, "
                                     "Without item: %s)" % (group_name, ", ".join(with_item), ", ".join(without_item)))


def checks_by_checkgroup():
    groups = {}
    for check_plugin_name, check in check_info.items():
        group_name = check["group"]
        if group_name:
            groups.setdefault(group_name, [])
            groups[group_name].append((check_plugin_name, check))
    return groups


# These caches both only hold the base names of the checks
def initialize_check_type_caches():
    snmp_cache = cmk_base.runtime_cache.get_set("check_type_snmp")
    snmp_cache.update(snmp_info.keys())

    tcp_cache = cmk_base.runtime_cache.get_set("check_type_tcp")
    for check_plugin_name, check in check_info.items():
        section_name = section_name_of(check_plugin_name)
        if section_name not in snmp_cache:
            tcp_cache.add(section_name)

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

def section_name_of(check_plugin_name):
    return check_plugin_name.split(".")[0]


def set_hostname(hostname):
    check_api._hostname = hostname


def set_service(check_plugin_name, descr):
    check_api._check_plugin_name   = check_plugin_name
    check_api._service_description = descr


def is_snmp_check(check_plugin_name):
    cache = cmk_base.runtime_cache.get_dict("is_snmp_check")

    try:
        return cache[check_plugin_name]
    except KeyError:
        snmp_checks = cmk_base.runtime_cache.get_set("check_type_snmp")

        result = section_name_of(check_plugin_name) in snmp_checks
        cache[check_plugin_name] = result
        return result


def is_tcp_check(check_plugin_name):
    cache = cmk_base.runtime_cache.get_dict("is_tcp_check")

    try:
        return cache[check_plugin_name]
    except KeyError:
        tcp_checks = cmk_base.runtime_cache.get_set("check_type_tcp")

        result = section_name_of(check_plugin_name) in tcp_checks
        cache[check_plugin_name] = result
        return result


def discoverable_tcp_checks():
    types = []
    for check_plugin_name, check in check_info.items():
        if is_tcp_check(check_plugin_name) and check["inventory_function"]:
            types.append(check_plugin_name)
    return sorted(types)


def discoverable_snmp_checks():
    types = []
    for check_plugin_name, check in check_info.items():
        if is_snmp_check(check_plugin_name) and check["inventory_function"]:
            types.append(check_plugin_name)
    return sorted(types)


# Compute parameters for a check honoring factory settings,
# default settings of user in main.mk, check_parameters[] and
# the values code in autochecks (given as parameter params)
def compute_check_parameters(host, checktype, item, params):
    if checktype not in check_info: # handle vanished checktype
        return None

    params = _update_with_default_check_parameters(checktype, params)
    params = _update_with_configured_check_parameters(host, checktype, item, params)

    return params


def _update_with_default_check_parameters(checktype, params):
    # Handle dictionary based checks
    def_levels_varname = check_info[checktype].get("default_levels_variable")

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
        check_context = _check_contexts[checktype]
        if def_levels_varname and def_levels_varname in check_context:
            def_levels = check_context[def_levels_varname]
            if type(def_levels) == dict:
                new_params.update(def_levels)

        # Merge params from inventory onto it
        new_params.update(params)
        params = new_params

    return params


def _update_with_configured_check_parameters(host, checktype, item, params):
    descr = config.service_description(host, checktype, item)

    # Get parameters configured via checkgroup_parameters
    entries = _get_checkgroup_parameters(host, checktype, item)

    # Get parameters configured via check_parameters
    entries += rulesets.service_extra_conf(host, descr, config.check_parameters)

    if entries:
        if _has_timespecific_params(entries):
            # some parameters include timespecific settings
            # these will be executed just before the check execution
            return TimespecificParamList(entries + [params])

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


def _has_timespecific_params(entries):
    for entry in entries:
        if isinstance(entry, dict) and "tp_default_value" in entry:
            return True
    return False


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


# TODO: Better move this function to config.py
def do_status_data_inventory_for(hostname):
    rules = config.active_checks.get('cmk_inv')
    if rules is None:
        return False

    # 'host_extra_conf' is already cached thus we can
    # use it after every check cycle.
    entries = rulesets.host_extra_conf(hostname, rules)

    if not entries:
        return False # No matching rule -> disable

    # Convert legacy rules to current dict format (just like the valuespec)
    params = {} if entries[0] is None else entries[0]

    return params.get('status_data_inventory', False)


def filter_by_management_board(hostname, found_check_plugin_names,
                               for_mgmt_board, for_discovery=False,
                               for_inventory=False):
    """
    In order to decide which check is used for which data source
    we have to filter the found check plugins. This is done via
    the check_info key "management_board". There are three values
    with the following meanings:
    - MGMT_ONLY
        These check plugins
        - are only used for management board data sources,
        - have the prefix 'mgmt_' in their name,
        - have the prefix 'Management Interface:' in their service description.
        - If there is an equivalent host check plugin then it must be 'HOST_ONLY'.

    - HOST_PRECEDENCE
        - Default value for all check plugins.
        - It does not have to be declared in the check_info.
        - Special situation for SNMP management boards:
            - If a host is not a SNMP host these checks are used for
              the SNMP management boards.
            - If a host is a SNMP host these checks are used for
              the host itself.

    - HOST_ONLY
        These check plugins
        - are used for 'real' host data sources, not for host management board data sources
        - there is an equivalent 'MGMT_ONLY'-management board check plugin.
    """

    mgmt_only, host_precedence_snmp, host_only_snmp, host_precedence_tcp, host_only_tcp =\
        _get_categorized_check_plugins(found_check_plugin_names, for_inventory=for_inventory)

    final_collection = set()
    is_snmp_host = config.is_snmp_host(hostname)
    is_agent_host = config.is_agent_host(hostname)
    if not config.has_management_board(hostname):
        if is_snmp_host:
            final_collection.update(host_precedence_snmp)
            final_collection.update(host_only_snmp)
        if is_agent_host:
            final_collection.update(host_precedence_tcp)
            final_collection.update(host_only_tcp)
        return final_collection

    if for_mgmt_board:
        final_collection.update(mgmt_only)
        if not is_snmp_host:
            final_collection.update(host_precedence_snmp)
            if not for_discovery:
                # Migration from 1.4 to 1.5:
                # in 1.4 TCP hosts with SNMP management boards discovered TCP and
                # SNMP checks, eg. uptime and snmp_uptime.  During checking phase
                # these checks should be executed
                # further on.
                # In versions >= 1.5 there are management board specific check
                # plugins, eg. mgmt_snmp_uptime.
                # After a re-discovery Check_MK finds the uptime check plugin for
                # the TCP host and the mgmt_snmp_uptime check for the SNMP
                # management board. Moreover Check_MK eliminates 'HOST_ONLT'
                # checks like snmp_uptime.
                final_collection.update(host_only_snmp)
    else:
        if is_snmp_host:
            final_collection.update(host_precedence_snmp)
            final_collection.update(host_only_snmp)
        if is_agent_host:
            final_collection.update(host_precedence_tcp)
            final_collection.update(host_only_tcp)
    return final_collection


def _get_categorized_check_plugins(check_plugin_names, for_inventory=False):
    if for_inventory:
        is_snmp_check_f = cmk_base.inventory_plugins.is_snmp_plugin
        plugins_info = cmk_base.inventory_plugins.inv_info
    else:
        is_snmp_check_f = is_snmp_check
        plugins_info = check_info

    mgmt_only = set()
    host_precedence_snmp = set()
    host_precedence_tcp = set()
    host_only_snmp = set()
    host_only_tcp = set()

    for check_plugin_name in check_plugin_names:
        is_snmp_check_ = is_snmp_check_f(check_plugin_name)
        mgmt_board = _get_management_board_precedence(check_plugin_name, plugins_info)
        if mgmt_board == check_api.HOST_PRECEDENCE:
            if is_snmp_check_:
                host_precedence_snmp.add(check_plugin_name)
            else:
                host_precedence_tcp.add(check_plugin_name)

        elif mgmt_board == check_api.MGMT_ONLY:
            mgmt_only.add(check_plugin_name)

        elif mgmt_board == check_api.HOST_ONLY:
            if is_snmp_check_:
                host_only_snmp.add(check_plugin_name)
            else:
                host_only_tcp.add(check_plugin_name)

    return mgmt_only, host_precedence_snmp, host_only_snmp,\
           host_precedence_tcp, host_only_tcp


def _get_management_board_precedence(check_plugin_name, plugins_info):
    mgmt_board = plugins_info[check_plugin_name].get("management_board")
    if mgmt_board is None:
        return check_api.HOST_PRECEDENCE
    return mgmt_board
