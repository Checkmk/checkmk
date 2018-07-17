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
import sys
import copy
import marshal
import math
import ast
import py_compile
import struct
from collections import OrderedDict

import cmk.debug
import cmk.paths
from cmk.regex import regex, is_regex
import cmk.translations
import cmk.store as store
from cmk.exceptions import MKGeneralException, MKTerminate

import cmk_base
import cmk_base.console as console
import cmk_base.default_config as default_config
import cmk_base.check_utils
import cmk_base.utils
import cmk_base.check_api_utils as check_api_utils
import cmk_base.cleanup

# TODO: Prefix helper functions with "_".

# This is mainly needed for pylint to detect all available
# configuration options during static analysis. The defaults
# are loaded later with load_default_config() again.
from cmk_base.default_config import *

def get_variable_names():
    """Provides the list of all known configuration variables."""
    return [ k for k in default_config.__dict__.keys() if k[0] != "_" ]


def get_default_config():
    """Provides a dictionary containing the Check_MK default configuration"""
    cfg = {}
    for key in get_variable_names():
        value = getattr(default_config, key)

        if isinstance(value, (dict, list)):
            value = copy.deepcopy(value)

        cfg[key] = value
    return cfg


def load_default_config():
    globals().update(get_default_config())


def register(name, default_value):
    """Register a new configuration variable within Check_MK base."""
    setattr(default_config, name, default_value)


def _add_check_variables_to_default_config():
    """Add configuration variables registered by checks to config module"""
    default_config.__dict__.update(get_check_variable_defaults())


def _clear_check_variables_from_default_config(check_variable_names):
    """Remove previously registered check variables from the config module"""
    for varname in check_variable_names:
        try:
            delattr(default_config, varname)
        except AttributeError:
            pass


# Load user configured values of check related configuration variables
# into the check module to make it available during checking.
#
# In the same step we remove the check related configuration settings from the
# config module because they are not needed there anymore.
#
# And also remove it from the default config (in case it was present)
def set_check_variables_for_checks():
    global_dict = globals()
    cvn = check_variable_names()

    check_variables = {}
    for varname in cvn:
        check_variables[varname] = global_dict.pop(varname)

    set_check_variables(check_variables)
    _clear_check_variables_from_default_config(cvn)


#.
#   .--Read Config---------------------------------------------------------.
#   |        ____                _    ____             __ _                |
#   |       |  _ \ ___  __ _  __| |  / ___|___  _ __  / _(_) __ _          |
#   |       | |_) / _ \/ _` |/ _` | | |   / _ \| '_ \| |_| |/ _` |         |
#   |       |  _ <  __/ (_| | (_| | | |__| (_) | | | |  _| | (_| |         |
#   |       |_| \_\___|\__,_|\__,_|  \____\___/|_| |_|_| |_|\__, |         |
#   |                                                       |___/          |
#   +----------------------------------------------------------------------+
#   | Code for reading the configuration files.                            |
#   '----------------------------------------------------------------------'

def load(with_conf_d=True, validate_hosts=True, exclude_parents_mk=False):
    _initialize_config()

    vars_before_config = all_nonfunction_vars()

    _load_config(with_conf_d, exclude_parents_mk)
    _transform_mgmt_config_vars_from_140_to_150()
    _initialize_derived_config_variables()

    _perform_post_config_loading_actions()

    if validate_hosts:
        _verify_non_duplicate_hosts()

    # Such validation only makes sense when all checks have been loaded
    if all_checks_loaded():
        verify_non_invalid_variables(vars_before_config)

    verify_snmp_communities_type()


def load_packed_config():
    """Load the configuration for the CMK helpers of CMC

    These files are written by PackedConfig().

    Should have a result similar to the load() above. With the exception that the
    check helpers would only need check related config variables.

    The validations which are performed during load() also don't need to be performed.
    """
    PackedConfig().load()


def _initialize_config():
    _add_check_variables_to_default_config()
    load_default_config()


def _perform_post_config_loading_actions():
    """These tasks must be performed after loading the Check_MK base configuration"""
    # First cleanup things (needed for e.g. reloading the config)
    cmk_base.config_cache.clear_all()

    initialize_config_caches()

    # In case the checks are not loaded yet it seems the current mode
    # is not working with the checks. In this case also don't load the
    # static checks into the configuration.
    if all_checks_loaded():
        add_wato_static_checks_to_checks()
        initialize_check_caches()
        set_check_variables_for_checks()


def _load_config(with_conf_d, exclude_parents_mk):
    helper_vars = {
        "FILE_PATH"      : None,
        "FOLDER_PATH"    : None,
    }

    global_dict = globals()
    global_dict.update(helper_vars)

    for _f in _get_config_file_paths(with_conf_d):
        # During parent scan mode we must not read in old version of parents.mk!
        if exclude_parents_mk and _f.endswith("/parents.mk"):
            continue

        try:
            _hosts_before    = set(all_hosts)
            _clusters_before = set(clusters.keys())

            # Make the config path available as a global variable to
            # be used within the configuration file
            if _f.startswith(cmk.paths.check_mk_config_dir + "/"):
                _file_path = _f[len(cmk.paths.check_mk_config_dir) + 1:]
                global_dict.update({
                    "FILE_PATH"   : _file_path,
                    "FOLDER_PATH" : os.path.dirname(_file_path),
                })
            else:
                global_dict.update({
                    "FILE_PATH"   : None,
                    "FOLDER_PATH" : None,
                })

            execfile(_f, global_dict, global_dict)

            _new_hosts    = set(all_hosts).difference(_hosts_before)
            _new_clusters = set(clusters.keys()).difference(_clusters_before)

            set_folder_paths(_new_hosts.union(_new_clusters), _f)
        except Exception, e:
            if cmk.debug.enabled():
                raise
            elif sys.stderr.isatty():
                console.error("Cannot read in configuration file %s: %s\n", _f, e)
                sys.exit(1)

    # Cleanup global helper vars
    for helper_var in helper_vars.keys():
        del global_dict[helper_var]


def _transform_mgmt_config_vars_from_140_to_150():
    #FIXME We have to transform some configuration variables from host attributes
    # to cmk_base configuration variables because during the migration step from
    # 1.4.0 to 1.5.0 some config variables are not known in cmk_base. These variables
    # are 'management_protocol' and 'management_snmp_community'.
    # Clean this up one day!
    for hostname, attributes in host_attributes.iteritems():
        for name, var in [
            ('management_protocol',       management_protocol),
            ('management_snmp_community', management_snmp_credentials),
        ]:
            if attributes.get(name):
                var.setdefault(hostname, attributes[name])


# Create list of all files to be included during configuration loading
def _get_config_file_paths(with_conf_d):
    if with_conf_d:
        list_of_files = sorted(
            reduce(lambda a,b: a+b, [ [ "%s/%s" % (d, f) for f in fs if f.endswith(".mk")]
                   for d, _unused_sb, fs in os.walk(cmk.paths.check_mk_config_dir) ], []),
           cmp=_cmp_config_paths
        )
        list_of_files = [ cmk.paths.main_config_file ] + list_of_files
    else:
        list_of_files = [ cmk.paths.main_config_file ]

    for path in [ cmk.paths.final_config_file, cmk.paths.local_config_file ]:
        if os.path.exists(path):
            list_of_files.append(path)

    return list_of_files


def initialize_config_caches():
    collect_hosttags()


def _initialize_derived_config_variables():
    global service_service_levels, host_service_levels
    service_service_levels = extra_service_conf.get("_ec_sl", [])
    host_service_levels = extra_host_conf.get("_ec_sl", [])


def get_derived_config_variable_names():
    """These variables are computed from other configuration variables and not configured directly.

    The origin variable (extra_service_conf) should not be exported to the helper config. Only
    the service levels are needed."""
    return set([ "service_service_levels", "host_service_levels" ])


def _verify_non_duplicate_hosts():
    duplicates = duplicate_hosts()
    if duplicates:
        # TODO: Raise an exception
        console.error("Error in configuration: duplicate hosts: %s\n",
                                                ", ".join(duplicates))
        sys.exit(3)


# Add WATO-configured explicit checks to (possibly empty) checks
# statically defined in checks.
def add_wato_static_checks_to_checks():
    global checks

    static = []
    for entries in static_checks.values():
        for entry in entries:
            entry, rule_options = get_rule_options(entry)
            if rule_options.get("disabled"):
                continue

            # Parameters are optional
            if len(entry[0]) == 2:
                checktype, item = entry[0]
                params = None
            else:
                checktype, item, params = entry[0]
            if len(entry) == 3:
                taglist, hostlist = entry[1:3]
            else:
                hostlist = entry[1]
                taglist = []
            # Make sure, that for dictionary based checks
            # at least those keys defined in the factory
            # settings are present in the parameters
            if type(params) == dict:
                def_levels_varname = check_info[checktype].get("default_levels_variable")
                if def_levels_varname:
                    for key, value in factory_settings.get(def_levels_varname, {}).items():
                        if key not in params:
                            params[key] = value

            static.append((taglist, hostlist, checktype, item, params))

    # Note: We need to reverse the order of the static_checks. This is because
    # users assume that earlier rules have precedence over later ones. For static
    # checks that is important if there are two rules for a host with the same
    # combination of check type and item. When the variable 'checks' is evaluated,
    # *later* rules have precedence. This is not consistent with the rest, but a
    # result of this "historic implementation".
    static.reverse()

    # Now prepend to checks. That makes that checks variable have precedence
    # over WATO.
    checks = static + checks


def initialize_check_caches():
    single_host_checks = cmk_base.config_cache.get_dict("single_host_checks")
    multi_host_checks  = cmk_base.config_cache.get_list("multi_host_checks")

    for entry in checks:
        if len(entry) == 4 and type(entry[0]) == str:
            single_host_checks.setdefault(entry[0], []).append(entry)
        else:
            multi_host_checks.append(entry)


def set_folder_paths(new_hosts, filename):
    if not filename.startswith(cmk.paths.check_mk_config_dir):
        return

    path = filename[len(cmk.paths.check_mk_config_dir):]

    for hostname in strip_tags(new_hosts):
        host_paths[hostname] = path


def verify_non_invalid_variables(vars_before_config):
    # Check for invalid configuration variables
    vars_after_config = all_nonfunction_vars()
    ignored_variables = set(['vars_before_config', 'parts',
                             'seen_hostnames',
                             'taggedhost' ,'hostname',
                             'service_service_levels',
                             'host_service_levels'])

    found_invalid = 0
    for name in vars_after_config:
        if name not in ignored_variables and name not in vars_before_config:
            console.error("Invalid configuration variable '%s'\n", name)
            found_invalid += 1

    if found_invalid:
        console.error("--> Found %d invalid variables\n" % found_invalid)
        console.error("If you use own helper variables, please prefix them with _.\n")
        sys.exit(1)


def verify_snmp_communities_type():
    # Special handling for certain deprecated variables
    if type(snmp_communities) == dict:
        console.error("ERROR: snmp_communities cannot be a dict any more.\n")
        sys.exit(1)


def all_nonfunction_vars():
    return set([ name for name,value in globals().items()
                if name[0] != '_' and type(value) != type(lambda:0) ])


# Helper functions that determines the sort order of the
# configuration files. The following two rules are implemented:
# 1. *.mk files in the same directory will be read
#    according to their lexical order.
# 2. subdirectories in the same directory will be
#    scanned according to their lexical order.
# 3. subdirectories of a directory will always be read *after*
#    the *.mk files in that directory.
def _cmp_config_paths(a, b):
    pa = a.split('/')
    pb = b.split('/')
    return cmp(pa[:-1], pb[:-1]) or \
           cmp(len(pa), len(pb)) or \
           cmp(pa, pb)


class PackedConfig(object):
    """The precompiled host checks and the CMC Check_MK helpers use a
    "precompiled" part of the Check_MK configuration during runtime.

    a) They must not use the live config from etc/check_mk during
       startup. They are only allowed to load the config activated by
       the user.

    b) They must not load the whole Check_MK config. Because they only
       need the options needed for checking
    """

    # These variables are part of the Check_MK configuration, but are not needed
    # by the Check_MK keepalive mode, so exclude them from the packed config
    _skipped_config_variable_names = [
        "define_contactgroups",
        "define_hostgroups",
        "define_servicegroups",
        "service_contactgroups",
        "host_contactgroups",
        "service_groups",
        "host_groups",
        "contacts",
        "host_paths",
        "timeperiods",
        "extra_service_conf",
        "extra_host_conf",
        "extra_nagios_conf",
    ]

    def __init__(self):
        super(PackedConfig, self).__init__()
        self._path = os.path.join(cmk.paths.var_dir, "base", "precompiled_check_config.mk")


    def save(self):
        self._write(self._pack())


    def _pack(self):
        helper_config = (
            "#!/usr/bin/env python\n"
            "# encoding: utf-8\n"
            "# Created by Check_MK. Dump of the currently active configuration\n\n"
        )

        # These functions purpose is to filter out hosts which are monitored on different sites
        active_hosts    = all_active_hosts()
        active_clusters = all_active_clusters()
        def filter_all_hosts(all_hosts):
            all_hosts_red = []
            for host_entry in all_hosts:
                hostname = host_entry.split("|", 1)[0]
                if hostname in active_hosts:
                    all_hosts_red.append(host_entry)
            return all_hosts_red

        def filter_clusters(clusters):
            clusters_red = {}
            for cluster_entry, cluster_nodes in clusters.items():
                clustername = cluster_entry.split("|", 1)[0]
                if clustername in active_clusters:
                    clusters_red[cluster_entry] = cluster_nodes
            return clusters_red

        def filter_hostname_in_dict(values):
            values_red = {}
            for hostname, attributes in values.items():
                if hostname in active_hosts:
                    values_red[hostname] = attributes
            return values_red

        filter_var_functions = {
            "all_hosts"                : filter_all_hosts,
            "clusters"                 : filter_clusters,
            "host_attributes"          : filter_hostname_in_dict,
            "ipaddresses"              : filter_hostname_in_dict,
            "ipv6addresses"            : filter_hostname_in_dict,
            "explicit_snmp_communities": filter_hostname_in_dict,
            "hosttags"                 : filter_hostname_in_dict
        }

        #
        # Add modified Check_MK base settings
        #

        variable_defaults = get_default_config()
        derived_config_variable_names = get_derived_config_variable_names()

        global_variables = globals()

        for varname in get_variable_names() + list(derived_config_variable_names):
            if varname in self._skipped_config_variable_names:
                continue

            val = global_variables[varname]

            if varname not in derived_config_variable_names and val == variable_defaults[varname]:
                continue

            if not self._packable(varname, val):
                continue

            if varname in filter_var_functions:
                val = filter_var_functions[varname](val)

            helper_config += "\n%s = %r\n" % (varname, val)

        #
        # Add modified check specific Check_MK base settings
        #

        check_variable_defaults = get_check_variable_defaults()

        for varname, val in get_check_variables().items():
            if val == check_variable_defaults[varname]:
                continue

            if not self._packable(varname, val):
                continue

            helper_config += "\n%s = %r\n" % (varname, val)

        return helper_config


    def _packable(self, varname, val):
        """Checks whether or not a variable can be written to the config.mk
        and read again from it."""
        if type(val) in [ int, str, unicode, bool ] or not val:
            return True

        try:
            eval(repr(val))
            return True
        except:
            return False


    def _write(self, helper_config):
        store.makedirs(os.path.dirname(self._path))

        store.save_file(self._path + ".orig", helper_config + "\n")

        import marshal
        code = compile(helper_config, '<string>', 'exec')
        with open(self._path + ".compiled", "w") as compiled_file:
            marshal.dump(code, compiled_file)

        os.rename(self._path + ".compiled", self._path)


    def load(self):
        _initialize_config()
        exec(marshal.load(open(self._path)), globals())
        _perform_post_config_loading_actions()


#.
#   .--Host tags-----------------------------------------------------------.
#   |              _   _           _     _                                 |
#   |             | | | | ___  ___| |_  | |_ __ _  __ _ ___                |
#   |             | |_| |/ _ \/ __| __| | __/ _` |/ _` / __|               |
#   |             |  _  | (_) \__ \ |_  | || (_| | (_| \__ \               |
#   |             |_| |_|\___/|___/\__|  \__\__,_|\__, |___/               |
#   |                                             |___/                    |
#   +----------------------------------------------------------------------+
#   |  Helper functions for dealing with host tags                         |
#   '----------------------------------------------------------------------'

def strip_tags(tagged_hostlist):
    cache = cmk_base.config_cache.get_dict("strip_tags")

    cache_id = tuple(tagged_hostlist)
    try:
        return cache[cache_id]
    except KeyError:
        result = [h.split('|', 1)[0] for h in tagged_hostlist]
        cache[cache_id] = result
        return result


def tags_of_host(hostname):
    """Returns the list of all configured tags of a host. In case
    a host has no tags configured or is not known, it returns an
    empty list."""
    hosttags = cmk_base.config_cache.get_dict("hosttags")
    try:
        return hosttags[hostname]
    except KeyError:
        return []


def collect_hosttags():
    hosttags = cmk_base.config_cache.get_dict("hosttags")
    for tagged_host in all_hosts + clusters.keys():
        parts = tagged_host.split("|")
        hosttags[parts[0]] = sorted(parts[1:])


#.
#   .--HostCollections-----------------------------------------------------.
#   | _   _           _    ____      _ _           _   _                   |
#   || | | | ___  ___| |_ / ___|___ | | | ___  ___| |_(_) ___  _ __  ___   |
#   || |_| |/ _ \/ __| __| |   / _ \| | |/ _ \/ __| __| |/ _ \| '_ \/ __|  |
#   ||  _  | (_) \__ \ |_| |__| (_) | | |  __/ (__| |_| | (_) | | | \__ \  |
#   ||_| |_|\___/|___/\__|\____\___/|_|_|\___|\___|\__|_|\___/|_| |_|___/  |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'


# Returns a set of all active hosts
def all_active_hosts():
    cache = cmk_base.config_cache.get_set("all_active_hosts")
    if not cache.is_populated():
        cache.update(all_active_realhosts(), all_active_clusters())
        cache.set_populated()
    return cache


# Returns a set of all host names to be handled by this site
# hosts of other sitest or disabled hosts are excluded
def all_active_realhosts():
    active_realhosts = cmk_base.config_cache.get_set("active_realhosts")

    if not active_realhosts.is_populated():
        active_realhosts.update(filter_active_hosts(all_configured_realhosts()))
        active_realhosts.set_populated()

    return active_realhosts


# Returns a set of all cluster host names to be handled by
# this site hosts of other sitest or disabled hosts are excluded
def all_active_clusters():
    active_clusters = cmk_base.config_cache.get_set("active_clusters")

    if not active_clusters.is_populated():
        active_clusters.update(filter_active_hosts(all_configured_clusters()))
        active_clusters.set_populated()

    return active_clusters


# Returns a set of all hosts, regardless if currently
# disabled or monitored on a remote site.
def all_configured_hosts():
    cache = cmk_base.config_cache.get_set("all_configured_hosts")
    if not cache.is_populated():
        cache.update(all_configured_realhosts(), all_configured_clusters())
        cache.set_populated()
    return cache


# Returns a set of all host names, regardless if currently
# disabled or monitored on a remote site. Does not return
# cluster hosts.
def all_configured_realhosts():
    cache = cmk_base.config_cache.get_set("all_configured_realhosts")
    if not cache.is_populated():
        cache.update(strip_tags(all_hosts))
        cache.set_populated()
    return cache


# Returns a set of all cluster names, regardless if currently
# disabled or monitored on a remote site. Does not return
# normal hosts.
def all_configured_clusters():
    cache = cmk_base.config_cache.get_set("all_configured_clusters")
    if not cache.is_populated():
        cache.update(strip_tags(clusters.keys()))
        cache.set_populated()
    return cache


# This function should only be used during duplicate host check! It has to work like
# all_active_hosts() but with the difference that duplicates are not removed.
def all_active_hosts_with_duplicates():
    # Only available with CEE
    if "shadow_hosts" in globals():
        shadow_host_entries = shadow_hosts.keys()
    else:
        shadow_host_entries = []

    return filter_active_hosts(strip_tags(all_hosts)  \
                               + strip_tags(clusters.keys()) \
                               + strip_tags(shadow_host_entries), keep_duplicates=True)


# Returns a set of active hosts for this site
def filter_active_hosts(hostlist, keep_offline_hosts=False, keep_duplicates=False):
    if only_hosts == None and distributed_wato_site == None:
        active_hosts = hostlist

    elif only_hosts == None:
        active_hosts = [ hostname for hostname in hostlist
                 if host_is_member_of_site(hostname, distributed_wato_site) ]

    elif distributed_wato_site == None:
        if keep_offline_hosts:
            active_hosts = hostlist
        else:
            active_hosts = [ hostname for hostname in hostlist
                     if in_binary_hostlist(hostname, only_hosts) ]

    else:
        active_hosts = [ hostname for hostname in hostlist
                 if (keep_offline_hosts or in_binary_hostlist(hostname, only_hosts))
                 and host_is_member_of_site(hostname, distributed_wato_site) ]

    if keep_duplicates:
        return active_hosts
    else:
        return set(active_hosts)


def duplicate_hosts():
    seen_hostnames = set([])
    duplicates = set([])

    for hostname in all_active_hosts_with_duplicates():
        if hostname in seen_hostnames:
            duplicates.add(hostname)
        else:
            seen_hostnames.add(hostname)

    return sorted(list(duplicates))


# Returns a list of all hosts which are associated with this site,
# but have been removed by the "only_hosts" rule. Normally these
# are the hosts which have the tag "offline".
#
# This is not optimized for performance, so use in specific situations.
def all_offline_hosts():
    hostlist = filter_active_hosts(all_configured_realhosts().union(all_configured_clusters()),
                                   keep_offline_hosts=True)

    return [ hostname for hostname in hostlist
             if not in_binary_hostlist(hostname, only_hosts) ]



def all_configured_offline_hosts():
    hostlist = all_configured_realhosts().union(all_configured_clusters())

    return set([ hostname for hostname in hostlist
             if not in_binary_hostlist(hostname, only_hosts) ])



#.
#   .--Hosts---------------------------------------------------------------.
#   |                       _   _           _                              |
#   |                      | | | | ___  ___| |_ ___                        |
#   |                      | |_| |/ _ \/ __| __/ __|                       |
#   |                      |  _  | (_) \__ \ |_\__ \                       |
#   |                      |_| |_|\___/|___/\__|___/                       |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |  Helper functions for dealing with hosts.                            |
#   '----------------------------------------------------------------------'

def host_is_member_of_site(hostname, site):
    for tag in tags_of_host(hostname):
        if tag.startswith("site:"):
            return site == tag[5:]
    # hosts without a site: tag belong to all sites
    return True


def alias_of(hostname, fallback):
    aliases = host_extra_conf(hostname, extra_host_conf.get("alias", []))
    if len(aliases) == 0:
        if fallback:
            return fallback
        else:
            return hostname
    else:
        return aliases[0]


def get_additional_ipaddresses_of(hostname):
    #TODO Regarding the following configuration variables from WATO
    # there's no inheritance, thus we use 'host_attributes'.
    # Better would be to use cmk_base configuration variables,
    # eg. like 'management_protocol'.
    return (host_attributes.get(hostname, {}).get("additional_ipv4addresses", []),
            host_attributes.get(hostname, {}).get("additional_ipv6addresses", []))


def parents_of(hostname):
    par = host_extra_conf(hostname, parents)
    # Use only those parents which are defined and active in
    # all_hosts.
    used_parents = []
    for p in par:
        ps = p.split(",")
        for pss in ps:
            if pss in all_active_realhosts():
                used_parents.append(pss)
    return used_parents


# If host is node of one or more clusters, return a list of the cluster host names.
# If not, return an empty list.
def clusters_of(hostname):
    cache = cmk_base.config_cache.get_dict("clusters_of")
    if not cache.is_populated():
        for cluster, hosts in clusters.items():
            clustername = cluster.split('|', 1)[0]
            for name in hosts:
                cache.setdefault(name, []).append(clustername)
        cache.set_populated()

    return cache.get(hostname, [])


#
# Agent type
#

def is_tcp_host(hostname):
    return in_binary_hostlist(hostname, tcp_hosts)


def is_snmp_host(hostname):
    return in_binary_hostlist(hostname, snmp_hosts)


def is_ping_host(hostname):
    import cmk_base.piggyback as piggyback
    return not is_snmp_host(hostname) \
       and not is_tcp_host(hostname) \
       and not piggyback.has_piggyback_raw_data(piggyback_max_cachefile_age, hostname) \
       and not has_management_board(hostname)


def is_dual_host(hostname):
    return is_tcp_host(hostname) and is_snmp_host(hostname)


def is_all_agents_host(hostname):
    return "all-agents" in tags_of_host(hostname)


def is_all_special_agents_host(hostname):
    return "all-agents" in tags_of_host(hostname)


#
# IPv4/IPv6
#

def is_ipv6_primary(hostname):
    """Whether or not the given host is configured to be monitored
    primarily via IPv6."""
    dual_stack_host = is_ipv4v6_host(hostname)
    return (not dual_stack_host and is_ipv6_host(hostname)) \
            or (dual_stack_host and _primary_ip_address_family_of(hostname) == "ipv6")


def _primary_ip_address_family_of(hostname):
    rules = host_extra_conf(hostname, primary_address_family)
    if rules:
        return rules[0]
    return "ipv4"


def is_ipv4v6_host(hostname):
    tags = tags_of_host(hostname)
    return "ip-v6" in tags and "ip-v4" in tags


def is_ipv6_host(hostname):
    return "ip-v6" in tags_of_host(hostname)


def is_ipv4_host(hostname):
    """Whether or not the given host is configured to be monitored via IPv4.
    This is the case when it is set to be explicit IPv4 or implicit
    (when host is not an IPv6 host and not a "No IP" host)"""
    tags = tags_of_host(hostname)

    if "ip-v4" in tags:
       return True

    return "ip-v6" not in tags and "no-ip" not in tags


def is_no_ip_host(hostname):
    """Whether or not the given host is configured not to be monitored via IP"""
    return "no-ip" in tags_of_host(hostname)

#
# Management board
#

def has_management_board(hostname):
    return management_protocol_of(hostname) is not None


def management_address_of(hostname):
    attributes_of_host = host_attributes.get(hostname, {})
    if attributes_of_host.get("management_address"):
        return attributes_of_host["management_address"]
    else:
        return ipaddresses.get(hostname)


def management_protocol_of(hostname):
    return management_protocol.get(hostname)


def management_credentials_of(hostname):
    protocol = management_protocol_of(hostname)
    if protocol == "snmp":
        credentials_variable, default_value = management_snmp_credentials, snmp_default_community
    elif protocol == "ipmi":
        credentials_variable, default_value = management_ipmi_credentials, None
    elif protocol is None:
        return None
    else:
        raise NotImplementedError()

    # First try to use the explicit configuration of the host
    # (set directly for a host or via folder inheritance in WATO)
    try:
        return credentials_variable[hostname]
    except KeyError:
        pass

    # If a rule matches, use the first rule for the management board protocol of the host
    rule_settings = host_extra_conf(hostname, management_board_config)
    for protocol, credentials in rule_settings:
        if protocol == management_protocol_of(hostname):
            return credentials

    return default_value


#
# Agent communication
#

def agent_port_of(hostname):
    ports = host_extra_conf(hostname, agent_ports)
    if len(ports) == 0:
        return agent_port
    else:
        return ports[0]


def tcp_connect_timeout_of(hostname):
    timeouts = host_extra_conf(hostname, tcp_connect_timeouts)
    if len(timeouts) == 0:
        return tcp_connect_timeout
    else:
        return timeouts[0]


def agent_encryption_of(hostname):
    settings = host_extra_conf(hostname, agent_encryption)
    if settings:
        return settings[0]
    else:
        return {'use_regular': 'disable',
                'use_realtime': 'enforce'}


def agent_target_version(hostname):
    agent_target_versions = host_extra_conf(hostname, check_mk_agent_target_versions)
    if agent_target_versions:
        spec = agent_target_versions[0]
        if spec == "ignore":
            return None
        elif spec == "site":
            return cmk.__version__
        elif type(spec) == str:
            # Compatibility to old value specification format (a single version string)
            return spec
        elif spec[0] == 'specific':
            return spec[1]
        else:
            return spec # return the whole spec in case of an "at least version" config


#
# SNMP
#

# Determine SNMP community for a specific host.  It the host is found
# int the map snmp_communities, that community is returned. Otherwise
# the snmp_default_community is returned (wich is preset with
# "public", but can be overridden in main.mk
def snmp_credentials_of(hostname):
    try:
        return explicit_snmp_communities[hostname]
    except KeyError:
        pass

    communities = host_extra_conf(hostname, snmp_communities)
    if len(communities) > 0:
        return communities[0]

    # nothing configured for this host -> use default
    return snmp_default_community


def snmp_character_encoding_of(hostname):
    entries = host_extra_conf(hostname, snmp_character_encodings)
    if len(entries) > 0:
        return entries[0]


def snmp_timing_of(hostname):
    timing = host_extra_conf(hostname, snmp_timing)
    if len(timing) > 0:
        return timing[0]
    else:
        return {}


def snmpv3_contexts_of(hostname):
    return host_extra_conf(hostname, snmpv3_contexts)


def oid_range_limits_of(hostname):
    return host_extra_conf(hostname, snmp_limit_oid_range)


def snmp_port_of(hostname):
    ports = host_extra_conf(hostname, snmp_ports)
    if len(ports) == 0:
        return None # do not specify a port, use default
    else:
        return ports[0]


def is_snmpv3_host(hostname):
    return type(snmp_credentials_of(hostname)) == tuple


def is_bulkwalk_host(hostname):
    if bulkwalk_hosts:
        return in_binary_hostlist(hostname, bulkwalk_hosts)
    else:
        return False


def bulk_walk_size_of(hostname):
    bulk_sizes = host_extra_conf(hostname, snmp_bulk_size)
    if not bulk_sizes:
        return 10
    else:
        return bulk_sizes[0]


def is_snmpv2c_host(hostname):
    return is_bulkwalk_host(hostname) or \
        in_binary_hostlist(hostname, snmpv2c_hosts)


def is_usewalk_host(hostname):
    return in_binary_hostlist(hostname, usewalk_hosts)


def is_inline_snmp_host(hostname):
    # TODO: Better use "inline_snmp" once we have moved the code to an own module
    has_inline_snmp = "netsnmp" in sys.modules
    return has_inline_snmp and use_inline_snmp \
           and not in_binary_hostlist(hostname, non_inline_snmp_hosts)


#
# Groups
#

def hostgroups_of(hostname):
    return host_extra_conf(hostname, host_groups)


def summary_hostgroups_of(hostname):
    return host_extra_conf(hostname, summary_host_groups)


def contactgroups_of(hostname):
    cgrs = []

    # host_contactgroups may take single values as well as
    # lists as item value. Of all list entries only the first
    # one is used. The single-contact-groups entries are all
    # recognized.
    first_list = True
    for entry in host_extra_conf(hostname, host_contactgroups):
        if type(entry) == list and first_list:
            cgrs += entry
            first_list = False
        else:
            cgrs.append(entry)

    if monitoring_core == "nagios" and enable_rulebased_notifications:
        cgrs.append("check-mk-notify")

    return list(set(cgrs))

#
# Misc
#

def exit_code_spec(hostname):
    spec = {}
    specs = host_extra_conf(hostname, check_mk_exit_status)
    for entry in specs[::-1]:
        spec.update(entry)
    return spec


def check_period_of(hostname, service):
    periods = service_extra_conf(hostname, service, check_periods)
    if periods:
        period = periods[0]
        if period == "24X7":
            return None
        else:
            return period
    else:
        return None


def check_interval_of(hostname, section_name):
    if not cmk_base.cmk_base.check_utils.is_snmp_check(section_name):
        return # no values at all for non snmp checks

    # Previous to 1.5 "match" could be a check name (including subchecks) instead of
    # only main check names -> section names. This has been cleaned up, but we still
    # need to be compatible. Strip of the sub check part of "match".
    for match, minutes in host_extra_conf(hostname, snmp_check_interval):
        if match is None or match.split(".")[0] == section_name:
            return minutes # use first match

#.
#   .--Cluster-------------------------------------------------------------.
#   |                    ____ _           _                                |
#   |                   / ___| |_   _ ___| |_ ___ _ __                     |
#   |                  | |   | | | | / __| __/ _ \ '__|                    |
#   |                  | |___| | |_| \__ \ ||  __/ |                       |
#   |                   \____|_|\__,_|___/\__\___|_|                       |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Code dealing with clusters (virtual hosts that are used to deal with |
#   | services that can move between physical nodes.                       |
#   '----------------------------------------------------------------------'

# Checks whether or not the given host is a cluster host
def is_cluster(hostname):
    # all_configured_clusters() needs to be used, because this function affects
    # the agent bakery, which needs all configured hosts instead of just the hosts
    # of this site
    return hostname in all_configured_clusters()


# Returns the nodes of a cluster, or None if hostname is not a cluster
def nodes_of(hostname):
    nodes_of_cache = cmk_base.config_cache.get_dict("nodes_of")
    nodes = nodes_of_cache.get(hostname, False)
    if nodes != False:
        return nodes

    for tagged_hostname, nodes in clusters.items():
        if hostname == tagged_hostname.split("|")[0]:
            nodes_of_cache[hostname] = nodes
            return nodes

    nodes_of_cache[hostname] = None
    return None


# Determine weather a service (found on a physical host) is a clustered
# service and - if yes - return the cluster host of the service. If
# no, returns the hostname of the physical host.
def host_of_clustered_service(hostname, servicedesc):
    the_clusters = clusters_of(hostname)
    if not the_clusters:
        return hostname

    cluster_mapping = service_extra_conf(hostname, servicedesc, clustered_services_mapping)
    for cluster in cluster_mapping:
        # Check if the host is in this cluster
        if cluster in the_clusters:
            return cluster

    # 1. New style: explicitly assigned services
    for cluster, conf in clustered_services_of.items():
        nodes = nodes_of(cluster)
        if not nodes:
            raise MKGeneralException("Invalid entry clustered_services_of['%s']: %s is not a cluster." %
                   (cluster, cluster))
        if hostname in nodes and \
            in_boolean_serviceconf_list(hostname, servicedesc, conf):
            return cluster

    # 1. Old style: clustered_services assumes that each host belong to
    #    exactly on cluster
    if in_boolean_serviceconf_list(hostname, servicedesc, clustered_services):
        return the_clusters[0]

    return hostname


#.
#   .--Services------------------------------------------------------------.
#   |                ____                  _                               |
#   |               / ___|  ___ _ ____   _(_) ___ ___  ___                 |
#   |               \___ \ / _ \ '__\ \ / / |/ __/ _ \/ __|                |
#   |                ___) |  __/ |   \ V /| | (_|  __/\__ \                |
#   |               |____/ \___|_|    \_/ |_|\___\___||___/                |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Service related helper functions                                     |
#   '----------------------------------------------------------------------'

# Renaming of service descriptions while keeping backward compatibility with
# existing installations.
# Synchronize with htdocs/wato.py and plugins/wato/check_mk_configuration.py!

# Cleanup! .. some day
def _get_old_cmciii_temp_description(item):
    if "Temperature" in item:
        return False, item # old item format, no conversion

    parts = item.split(" ")
    if parts[0] == "Ambient":
        return False, "%s Temperature" % parts[1]

    elif len(parts) == 2:
        return False, "%s %s.Temperature" % (parts[1], parts[0])

    else:
        if parts[1] == "LCP":
            parts[1] = "Liquid_Cooling_Package"
        return False, "%s %s.%s-Temperature" % (parts[1], parts[0], parts[2])


_old_service_descriptions = {
    "df"                               : "fs_%s",
    "df_netapp"                        : "fs_%s",
    "df_netapp32"                      : "fs_%s",
    "esx_vsphere_datastores"           : "fs_%s",
    "hr_fs"                            : "fs_%s",
    "vms_diskstat.df"                  : "fs_%s",
    "zfsget"                           : "fs_%s",
    "ps"                               : "proc_%s",
    "ps.perf"                          : "proc_%s",
    "wmic_process"                     : "proc_%s",
    "services"                         : "service_%s",
    "logwatch"                         : "LOG %s",
    "logwatch.groups"                  : "LOG %s",
    "hyperv_vm"                        : "hyperv_vms",
    "ibm_svc_mdiskgrp"                 : "MDiskGrp %s",
    "ibm_svc_system"                   : "IBM SVC Info",
    "ibm_svc_systemstats.diskio"       : "IBM SVC Throughput %s Total",
    "ibm_svc_systemstats.iops"         : "IBM SVC IOPS %s Total",
    "ibm_svc_systemstats.disk_latency" : "IBM SVC Latency %s Total",
    "ibm_svc_systemstats.cache"        : "IBM SVC Cache Total",
    "mknotifyd"                        : "Notification Spooler %s",
    "mknotifyd.connection"             : "Notification Connection %s",

    "casa_cpu_temp"                    : "Temperature %s",
    "cmciii.temp"                      : _get_old_cmciii_temp_description,
    "cmciii.psm_current"               : "%s",
    "cmciii_lcp_airin"                 : "LCP Fanunit Air IN",
    "cmciii_lcp_airout"                : "LCP Fanunit Air OUT",
    "cmciii_lcp_water"                 : "LCP Fanunit Water %s",
    "etherbox.temp"                    : "Sensor %s",
    # While using the old description, don't append the item, even when discovered
    # with the new check which creates an item.
    "liebert_bat_temp"                 : lambda item: (False, "Battery Temp"),
    "nvidia.temp"                      : "Temperature NVIDIA %s",
    "ups_bat_temp"                     : "Temperature Battery %s",
    "innovaphone_temp"                 : lambda item: (False, "Temperature"),
    "enterasys_temp"                   : lambda item: (False, "Temperature"),
    "raritan_emx"                      : "Rack %s",
    "raritan_pdu_inlet"                : "Input Phase %s",
    "postfix_mailq"                    : lambda item: (False, "Postfix Queue"),
    "nullmailer_mailq"                 : lambda item: (False, "Nullmailer Queue"),
    "barracuda_mailqueues"             : lambda item: (False, "Mail Queue"),
    "qmail_stats"                      : lambda item: (False, "Qmail Queue"),
    "mssql_backup"                     : "%s Backup",
    "mssql_counters.cache_hits"        : "%s",
    "mssql_counters.transactions"      : "%s Transactions",
    "mssql_counters.locks"             : "%s Locks",
    "mssql_counters.sqlstats"          : "%s",
    "mssql_counters.pageactivity"      : "%s Page Activity",
    "mssql_counters.locks_per_batch"   : "%s Locks per Batch",
    "mssql_counters.file_sizes"        : "%s File Sizes",
    "mssql_databases"                  : "%s Database",
    "mssql_datafiles"                  : "Datafile %s",
    "mssql_tablespaces"                : "%s Sizes",
    "mssql_transactionlogs"            : "Transactionlog %s",
    "mssql_versions"                   : "%s Version",

}

def service_description(hostname, check_plugin_name, item):
    if check_plugin_name not in check_info:
        if item:
            return "Unimplemented check %s / %s" % (check_plugin_name, item)
        else:
            return "Unimplemented check %s" % check_plugin_name

    # use user-supplied service description, if available
    add_item = True
    descr_format = service_descriptions.get(check_plugin_name)
    if not descr_format:
        # handle renaming for backward compatibility
        if check_plugin_name in _old_service_descriptions and \
            check_plugin_name not in use_new_descriptions_for:

            # Can be a fucntion to generate the old description more flexible.
            old_descr = _old_service_descriptions[check_plugin_name]
            if callable(old_descr):
                add_item, descr_format = old_descr(item)
            else:
                descr_format = old_descr

        else:
            descr_format = check_info[check_plugin_name]["service_description"]

    if type(descr_format) == str:
        descr_format = descr_format.decode("utf-8")

    # Note: we strip the service description (remove spaces).
    # One check defines "Pages %s" as a description, but the item
    # can by empty in some cases. Nagios silently drops leading
    # and trailing spaces in the configuration file.
    if add_item and type(item) in [str, unicode, int, long]:
        if "%s" not in descr_format:
            descr_format += " %s"
        descr = descr_format % (item,)
    else:
        descr = descr_format

    if "%s" in descr:
        raise MKGeneralException("Found '%%s' in service description (Host: %s, Check type: %s, Item: %s). "
                                 "Please try to rediscover the service to fix this issue." % \
                                 (hostname, check_plugin_name, item))

    return get_final_service_description(hostname, descr)


_old_active_check_service_descriptions = {
    "http": lambda params: (params[0][1:] if params[0].startswith("^")
                            else "HTTP %s" % params[0])
}


def active_check_service_description(hostname, active_check_name, params):
    if active_check_name not in active_check_info:
        return "Unimplemented check %s" % active_check_name

    if (active_check_name in _old_active_check_service_descriptions and
            active_check_name not in use_new_descriptions_for):
        description = _old_active_check_service_descriptions[active_check_name](params)
    else:
        act_info = active_check_info[active_check_name]
        description = act_info["service_description"](params)

    description = description.replace('$HOSTNAME$', hostname)

    return get_final_service_description(hostname, description)


def get_final_service_description(hostname, description):
    translations = get_service_translations(hostname)
    if translations:
        # Translate
        description = cmk.translations.translate_service_description(translations, description)

    # Sanitize; Remove illegal characters from a service description
    description = description.strip()
    cache = cmk_base.config_cache.get_dict("final_service_description")
    try:
        new_description = cache[description]
    except KeyError:
        new_description = "".join([c for c in description
                          if c not in nagios_illegal_chars]).rstrip("\\")
        cache[description] = new_description

    return new_description


def service_ignored(hostname, check_plugin_name, service_description):
    if check_plugin_name and check_plugin_name in ignored_checktypes:
        return True
    if service_description != None \
       and in_boolean_serviceconf_list(hostname, service_description, ignored_services):
        return True
    if check_plugin_name and _checktype_ignored_for_host(hostname, check_plugin_name):
        return True
    return False


def _checktype_ignored_for_host(host, checktype):
    if checktype in ignored_checktypes:
        return True
    ignored = host_extra_conf(host, ignored_checks)
    for e in ignored:
        if checktype == e or (type(e) == list and checktype in e):
            return True
    return False


#.
#   .--Misc Helpers--------------------------------------------------------.
#   |        __  __ _            _   _      _                              |
#   |       |  \/  (_)___  ___  | | | | ___| |_ __   ___ _ __ ___          |
#   |       | |\/| | / __|/ __| | |_| |/ _ \ | '_ \ / _ \ '__/ __|         |
#   |       | |  | | \__ \ (__  |  _  |  __/ | |_) |  __/ |  \__ \         |
#   |       |_|  |_|_|___/\___| |_| |_|\___|_| .__/ \___|_|  |___/         |
#   |                                        |_|                           |
#   +----------------------------------------------------------------------+
#   | Different helper functions                                           |
#   '----------------------------------------------------------------------'

def is_cmc():
    """Whether or not the site is currently configured to use the Microcore."""
    return monitoring_core == "cmc"


def decode_incoming_string(s, encoding="utf-8"):
    try:
        return s.decode(encoding)
    except:
        return s.decode(fallback_agent_output_encoding)


def translate_piggyback_host(sourcehost, backedhost):
    translation = _get_piggyback_translations(sourcehost)

    # To make it possible to match umlauts we need to change the hostname
    # to a unicode string which can then be matched with regexes etc.
    # We assume the incoming name is correctly encoded in UTF-8
    backedhost = decode_incoming_string(backedhost)

    translated = cmk.translations.translate_hostname(translation, backedhost)

    return translated.encode('utf-8') # change back to UTF-8 encoded string


def _get_piggyback_translations(hostname):
    """Get a dict that specifies the actions to be done during the hostname translation"""
    rules = host_extra_conf(hostname, piggyback_translation)
    translations = {}
    for rule in rules[::-1]:
        translations.update(rule)
    return translations


def get_service_translations(hostname):
    translations_cache = cmk_base.config_cache.get_dict("service_description_translations")
    if hostname in translations_cache:
        return translations_cache[hostname]

    rules = host_extra_conf(hostname, service_description_translation)
    translations = {}
    for rule in rules[::-1]:
        for k, v in rule.items():
            if isinstance(v, list):
                translations.setdefault(k, set())
                translations[k] |= set(v)
            else:
                translations[k] = v

    translations_cache[hostname] = translations
    return translations

#.
#   .--Service rules-------------------------------------------------------.
#   |      ____                  _                       _                 |
#   |     / ___|  ___ _ ____   _(_) ___ ___   _ __ _   _| | ___  ___       |
#   |     \___ \ / _ \ '__\ \ / / |/ __/ _ \ | '__| | | | |/ _ \/ __|      |
#   |      ___) |  __/ |   \ V /| | (_|  __/ | |  | |_| | |  __/\__ \      |
#   |     |____/ \___|_|    \_/ |_|\___\___| |_|   \__,_|_|\___||___/      |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Service rule set matching                                            |
#   '----------------------------------------------------------------------'

def service_extra_conf(hostname, service, ruleset):
    """Compute outcome of a service rule set that has an item."""
    # When the requested host is part of the local sites configuration,
    # then use only the sites hosts for processing the rules
    with_foreign_hosts = hostname not in all_active_hosts()
    cache_id = id(ruleset), with_foreign_hosts
    ruleset_cache = cmk_base.config_cache.get_dict("converted_service_rulesets")
    try:
        ruleset = ruleset_cache[cache_id]
    except KeyError:
        ruleset = _convert_service_ruleset(ruleset, with_foreign_hosts)
        ruleset_cache[cache_id] = ruleset

    entries = []
    cache = cmk_base.config_cache.get_dict("extraconf_servicelist")
    for item, hosts, service_matchers in ruleset:
        if hostname in hosts:
            cache_id = service_matchers, service
            try:
                match = cache[cache_id]
            except KeyError:
                match = _in_servicematcher_list(service_matchers, service)
                cache[cache_id] = match

            if match:
                entries.append(item)
    return entries


def _convert_service_ruleset(ruleset, with_foreign_hosts):
    new_rules = []
    for rule in ruleset:
        rule, rule_options = get_rule_options(rule)
        if rule_options.get("disabled"):
            continue

        num_elements = len(rule)
        if num_elements == 3:
            item, hostlist, servlist = rule
            tags = []
        elif num_elements == 4:
            item, tags, hostlist, servlist = rule
        else:
            raise MKGeneralException("Invalid rule '%r' in service configuration "
                                     "list: must have 3 or 4 elements" % (rule,))

        # Directly compute set of all matching hosts here, this
        # will avoid recomputation later
        hosts = all_matching_hosts(tags, hostlist, with_foreign_hosts)

        # And now preprocess the configured patterns in the servlist
        new_rules.append((item, hosts, _convert_pattern_list(servlist)))

    return new_rules


# Compute outcome of a service rule set that just say yes/no
def in_boolean_serviceconf_list(hostname, service_description, ruleset):
    # When the requested host is part of the local sites configuration,
    # then use only the sites hosts for processing the rules
    with_foreign_hosts = hostname not in all_active_hosts()
    cache_id = id(ruleset), with_foreign_hosts
    ruleset_cache = cmk_base.config_cache.get_dict("converted_service_rulesets")
    try:
        ruleset = ruleset_cache[cache_id]
    except KeyError:
        ruleset = _convert_boolean_service_ruleset(ruleset, with_foreign_hosts)
        ruleset_cache[cache_id] = ruleset

    cache = cmk_base.config_cache.get_dict("extraconf_servicelist")
    for negate, hosts, service_matchers in ruleset:
        if hostname in hosts:
            cache_id = service_matchers, service_description
            try:
                match = cache[cache_id]
            except KeyError:
                match = _in_servicematcher_list(service_matchers, service_description)
                cache[cache_id] = match

            if match:
                return not negate
    return False # no match. Do not ignore


def _convert_boolean_service_ruleset(ruleset, with_foreign_hosts):
    new_rules = []
    for rule in ruleset:
        entry, rule_options = get_rule_options(rule)
        if rule_options.get("disabled"):
            continue

        if entry[0] == NEGATE: # this entry is logically negated
            negate = True
            entry = entry[1:]
        else:
            negate = False

        if len(entry) == 2:
            hostlist, servlist = entry
            tags = []
        elif len(entry) == 3:
            tags, hostlist, servlist = entry
        else:
            raise MKGeneralException("Invalid entry '%r' in configuration: "
                                     "must have 2 or 3 elements" % (entry,))

        # Directly compute set of all matching hosts here, this
        # will avoid recomputation later
        hosts = all_matching_hosts(tags, hostlist, with_foreign_hosts)
        new_rules.append((negate, hosts, _convert_pattern_list(servlist)))

    return new_rules


#.
#   .--Host rulesets-------------------------------------------------------.
#   |      _   _           _                _                _             |
#   |     | | | | ___  ___| |_   _ __ _   _| | ___  ___  ___| |_ ___       |
#   |     | |_| |/ _ \/ __| __| | '__| | | | |/ _ \/ __|/ _ \ __/ __|      |
#   |     |  _  | (_) \__ \ |_  | |  | |_| | |  __/\__ \  __/ |_\__ \      |
#   |     |_| |_|\___/|___/\__| |_|   \__,_|_|\___||___/\___|\__|___/      |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Host ruleset matching                                                |
#   '----------------------------------------------------------------------'

def host_extra_conf(hostname, ruleset):
    # When the requested host is part of the local sites configuration,
    # then use only the sites hosts for processing the rules
    with_foreign_hosts = hostname not in all_active_hosts()

    ruleset_cache = cmk_base.config_cache.get_dict("converted_host_rulesets")
    cache_id = id(ruleset), with_foreign_hosts

    conf_cache = cmk_base.config_cache.get_dict("host_extra_conf")

    try:
        ruleset = ruleset_cache[cache_id]
    except KeyError:
        ruleset = _convert_host_ruleset(ruleset, with_foreign_hosts)
        ruleset_cache[cache_id] = ruleset

        # TODO: LM: Why is this not on one indent level upper?
        #           The regular case of the above exception handler
        #           assigns "ruleset", but it is never used. Is this OK?
        #           And if it is OK, why is it different to service_extra_conf()?

        # Generate single match cache
        conf_cache[cache_id] = {}
        for item, hostname_list in ruleset:
            for name in hostname_list:
                conf_cache[cache_id].setdefault(name, []).append(item)

    if hostname not in conf_cache[cache_id]:
        return []

    return conf_cache[cache_id][hostname]


def _convert_host_ruleset(ruleset, with_foreign_hosts):
    new_rules = []
    if len(ruleset) == 1 and ruleset[0] == "":
        console.warning('deprecated entry [ "" ] in host configuration list')

    for rule in ruleset:
        item, tags, hostlist, rule_options = parse_host_rule(rule)
        if rule_options.get("disabled"):
            continue

        # Directly compute set of all matching hosts here, this
        # will avoid recomputation later
        new_rules.append((item, all_matching_hosts(tags, hostlist, with_foreign_hosts)))

    return new_rules


def host_extra_conf_merged(hostname, conf):
    rule_dict = {}
    for rule in host_extra_conf(hostname, conf):
        for key, value in rule.items():
            rule_dict.setdefault(key, value)
    return rule_dict

#.
#   .--Host matching-------------------------------------------------------.
#   |  _   _           _                     _       _     _               |
#   | | | | | ___  ___| |_   _ __ ___   __ _| |_ ___| |__ (_)_ __   __ _   |
#   | | |_| |/ _ \/ __| __| | '_ ` _ \ / _` | __/ __| '_ \| | '_ \ / _` |  |
#   | |  _  | (_) \__ \ |_  | | | | | | (_| | || (__| | | | | | | | (_| |  |
#   | |_| |_|\___/|___/\__| |_| |_| |_|\__,_|\__\___|_| |_|_|_| |_|\__, |  |
#   |                                                              |___/   |
#   +----------------------------------------------------------------------+
#   | Code for calculating the host condition matching of rules            |
#   '----------------------------------------------------------------------'


# TODO: Can we make this private?
def all_matching_hosts(tags, hostlist, with_foreign_hosts):
    """Returns a set containing the names of hosts that match the given
    tags and hostlist conditions."""
    cache_id = tuple(tags), tuple(hostlist), with_foreign_hosts
    cache = cmk_base.config_cache.get_dict("hostlist_match")

    try:
        return cache[cache_id]
    except KeyError:
        pass

    if with_foreign_hosts:
        valid_hosts = all_configured_hosts()
    else:
        valid_hosts = all_active_hosts()

    # Contains matched hosts
    matching = set([])

    # Check if the rule has only specific hosts set
    only_specific_hosts = not bool([x for x in hostlist if x[0] in ["@", "!", "~"]])

    # If no tags are specified and there are only specific hosts we already have the matches
    if not tags and only_specific_hosts:
        matching = valid_hosts.intersection(hostlist)
    # If no tags are specified and the hostlist only include @all (all hosts)
    elif not tags and hostlist == ALL_HOSTS:
        matching = valid_hosts
    else:
        # If the rule has only exact host restrictions, we can thin out the list of hosts to check
        if only_specific_hosts:
            hosts_to_check = valid_hosts.intersection(set(hostlist))
        else:
            hosts_to_check = valid_hosts

        for hostname in hosts_to_check:
            # When no tag matching is requested, do not filter by tags. Accept all hosts
            # and filter only by hostlist
            if in_extraconf_hostlist(hostlist, hostname) and \
               (not tags or hosttags_match_taglist(tags_of_host(hostname), tags)):
               matching.add(hostname)

    cache[cache_id] = matching
    return matching


def in_extraconf_hostlist(hostlist, hostname):
    """Whether or not the given host matches the hostlist.

    Entries in list are hostnames that must equal the hostname.
    Expressions beginning with ! are negated: if they match,
    the item is excluded from the list.

    Expressions beginning with ~ are treated as regular expression.
    Also the three special tags '@all', '@clusters', '@physical'
    are allowed.
    """

    # Migration help: print error if old format appears in config file
    # FIXME: When can this be removed?
    try:
        if hostlist[0] == "":
            raise MKGeneralException('Invalid empty entry [ "" ] in configuration')
    except IndexError:
        pass # Empty list, no problem.

    for hostentry in hostlist:
        if hostentry == '':
            raise MKGeneralException('Empty hostname in host list %r' % hostlist)
        negate = False
        use_regex = False
        if hostentry[0] == '@':
            if hostentry == '@all':
                return True
            ic = is_cluster(hostname)
            if hostentry == '@cluster' and ic:
                return True
            elif hostentry == '@physical' and not ic:
                return True

        # Allow negation of hostentry with prefix '!'
        else:
            if hostentry[0] == '!':
                hostentry = hostentry[1:]
                negate = True

            # Allow regex with prefix '~'
            if hostentry[0] == '~':
                hostentry = hostentry[1:]
                use_regex = True

        try:
            if not use_regex and hostname == hostentry:
                return not negate
            # Handle Regex. Note: hostname == True -> generic unknown host
            elif use_regex and hostname != True:
                if regex(hostentry).match(hostname) != None:
                    return not negate
        except MKGeneralException:
            if cmk.debug.enabled():
                raise

    return False



def in_binary_hostlist(hostname, conf):
    cache = cmk_base.config_cache.get_dict("in_binary_hostlist")
    cache_id = id(conf), hostname

    try:
        return cache[cache_id]
    except KeyError:
        pass

    # if we have just a list of strings just take it as list of hostnames
    if conf and type(conf[0]) == str:
        result = hostname in conf
        cache[cache_id] = result
    else:
        for entry in conf:
            entry, rule_options = get_rule_options(entry)
            if rule_options.get("disabled"):
                continue

            try:
                # Negation via 'NEGATE'
                if entry[0] == NEGATE:
                    entry = entry[1:]
                    negate = True
                else:
                    negate = False
                # entry should be one-tuple or two-tuple. Tuple's elements are
                # lists of strings. User might forget comma in one tuple. Then the
                # entry is the list itself.
                if type(entry) == list:
                    hostlist = entry
                    tags = []
                else:
                    if len(entry) == 1: # 1-Tuple with list of hosts
                        hostlist = entry[0]
                        tags = []
                    else:
                        tags, hostlist = entry

                if hosttags_match_taglist(tags_of_host(hostname), tags) and \
                       in_extraconf_hostlist(hostlist, hostname):
                    cache[cache_id] = not negate
                    break
            except:
                # TODO: Fix this too generic catching (+ bad error message)
                raise MKGeneralException("Invalid entry '%r' in host configuration list: "
                                   "must be tuple with 1 or 2 entries" % (entry,))
        else:
            cache[cache_id] = False

    return cache[cache_id]






def parse_host_rule(rule):
    rule, rule_options = get_rule_options(rule)

    num_elements = len(rule)
    if num_elements == 2:
        item, hostlist = rule
        tags = []
    elif num_elements == 3:
        item, tags, hostlist = rule
    else:
        raise MKGeneralException("Invalid entry '%r' in host configuration list: must "
                                 "have 2 or 3 entries" % (rule,))

    return item, tags, hostlist, rule_options


def get_rule_options(entry):
    """Get the options from a rule.

    Pick out the option element of a rule. Currently the options "disabled"
    and "comments" are being honored."""
    if type(entry[-1]) == dict:
        return entry[:-1], entry[-1]
    else:
        return entry, {}


def hosttags_match_taglist(hosttags, required_tags):
    """Check if a host fulfills the requirements of a tag list.

    The host must have all tags in the list, except
    for those negated with '!'. Those the host must *not* have!
    A trailing + means a prefix match."""

    for tag in required_tags:
        negate, tag = _parse_negated(tag)
        if tag and tag[-1] == '+':
            tag = tag[:-1]
            matches = False
            for t in hosttags:
                if t.startswith(tag):
                    matches = True
                    break

        else:
            matches = tag in hosttags

        if matches == negate:
            return False

    return True


def _parse_negated(pattern):
    # Allow negation of pattern with prefix '!'
    try:
        negate = pattern[0] == '!'
        if negate:
            pattern = pattern[1:]
    except IndexError:
        negate = False

    return negate, pattern


# Converts a regex pattern which is used to e.g. match services within Check_MK
# to a function reference to a matching function which takes one parameter to
# perform the matching and returns a two item tuple where the first element
# tells wether or not the pattern is negated and the second element the outcome
# of the match.
# This function tries to parse the pattern and return different kind of matching
# functions which can then be performed faster than just using the regex match.
def _convert_pattern(pattern):
    def is_infix_string_search(pattern):
        return pattern.startswith('.*') and not is_regex(pattern[2:])

    def is_exact_match(pattern):
        return pattern[-1] == '$' and not is_regex(pattern[:-1])

    def is_prefix_match(pattern):
        return pattern[-2:] == '.*' and not is_regex(pattern[:-2])

    if pattern == '':
        return False, lambda txt: True # empty patterns match always

    negate, pattern = _parse_negated(pattern)

    if is_exact_match(pattern):
        # Exact string match
        return negate, lambda txt: pattern[:-1] == txt

    elif is_infix_string_search(pattern):
        # Using regex to search a substring within text
        return negate, lambda txt: pattern[2:] in txt

    elif is_prefix_match(pattern):
        # prefix match with tailing .*
        pattern = pattern[:-2]
        return negate, lambda txt: txt[:len(pattern)] == pattern

    elif is_regex(pattern):
        # Non specific regex. Use real prefix regex matching
        return negate, lambda txt: regex(pattern).match(txt) != None

    else:
        # prefix match without any regex chars
        return negate, lambda txt: txt[:len(pattern)] == pattern


def _convert_pattern_list(patterns):
    return tuple([ _convert_pattern(p) for p in patterns ])


# Slow variant of checking wether a service is matched by a list
# of regexes - used e.g. by cmk --notify
def in_extraconf_servicelist(servicelist, service):
    return _in_servicematcher_list(_convert_pattern_list(servicelist), service)


def _in_servicematcher_list(service_matchers, item):
    for negate, func in service_matchers:
        result = func(item)
        if result:
            return not negate

    # no match in list -> negative answer
    return False


#.
#   .--Constants-----------------------------------------------------------.
#   |              ____                _              _                    |
#   |             / ___|___  _ __  ___| |_ __ _ _ __ | |_ ___              |
#   |            | |   / _ \| '_ \/ __| __/ _` | '_ \| __/ __|             |
#   |            | |__| (_) | | | \__ \ || (_| | | | | |_\__ \             |
#   |             \____\___/|_| |_|___/\__\__,_|_| |_|\__|___/             |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Some constants to be used in the configuration and at other places   |
#   '----------------------------------------------------------------------'

# Conveniance macros for host and service rules
PHYSICAL_HOSTS = [ '@physical' ] # all hosts but not clusters
CLUSTER_HOSTS  = [ '@cluster' ]  # all cluster hosts
ALL_HOSTS      = [ '@all' ]      # physical and cluster hosts
ALL_SERVICES   = [ "" ]          # optical replacement"
NEGATE         = '@negate'       # negation in boolean lists


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

def load_all_checks(get_check_api_context):
    """Load all checks and includes"""
    global _all_checks_loaded

    _initialize_data_structures()
    filelist = get_plugin_paths(cmk.paths.local_checks_dir, cmk.paths.checks_dir)
    load_checks(get_check_api_context, filelist)

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
def load_checks(get_check_api_context, filelist):
    cmk_global_vars = set(get_variable_names())

    loaded_files = set()
    ignored_variable_types = [ type(lambda: None), type(os) ]
    for f in filelist:
        if f[0] == "." or f[-1] == "~":
            continue # ignore editor backup / temp files

        file_name  = os.path.basename(f)
        if file_name in loaded_files:
            continue # skip already loaded files (e.g. from local)

        try:
            check_context = new_check_context(get_check_api_context)

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


# Constructs a new check context dictionary. It contains the whole check API.
def new_check_context(get_check_api_context):
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
    # NOTE: For better separation it would be better to copy the values, but
    # this might consume too much memory, so we simply reference them.
    context.update(get_check_api_context())
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
    local_path = os.path.join(cmk.paths.local_checks_dir, include_file_name)
    if os.path.exists(local_path):
        return local_path
    return os.path.join(cmk.paths.checks_dir, include_file_name)


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
        _precompile_plugin(path, precompiled_path)

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

    if long(os.stat(path).st_mtime) > origin_file_mtime:
        return False

    return True


def _precompile_plugin(path, precompiled_path):
    code = compile(open(path).read(), path, "exec")
    plugin_mtime = os.stat(path).st_mtime

    store.makedirs(os.path.dirname(precompiled_path))
    py_compile.compile(path, precompiled_path, doraise=True)


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
        section_name = cmk_base.check_utils.section_name_of(check_plugin_name)

        if type(info) != dict:
            # Convert check declaration from old style to new API
            check_function, service_description, has_perfdata, inventory_function = info
            if inventory_function == check_api_utils.no_discovery_possible:
                inventory_function = None

            check_info[check_plugin_name] = {
                "check_function"          : check_function,
                "service_description"     : service_description,
                "has_perfdata"            : bool(has_perfdata),
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
            section_name = cmk_base.check_utils.section_name_of(check_plugin_name)
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
        section_name = cmk_base.check_utils.section_name_of(check_plugin_name)
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
        section_name = cmk_base.check_utils.section_name_of(check_plugin_name)
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

def discoverable_tcp_checks():
    types = []
    for check_plugin_name, check in check_info.items():
        if cmk_base.check_utils.is_tcp_check(check_plugin_name) and check["inventory_function"]:
            types.append(check_plugin_name)
    return sorted(types)


def discoverable_snmp_checks():
    types = []
    for check_plugin_name, check in check_info.items():
        if cmk_base.check_utils.is_snmp_check(check_plugin_name) and check["inventory_function"]:
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
    descr = service_description(host, checktype, item)

    # Get parameters configured via checkgroup_parameters
    entries = _get_checkgroup_parameters(host, checktype, item)

    # Get parameters configured via check_parameters
    entries += service_extra_conf(host, descr, check_parameters)

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
    rules = checkgroup_parameters.get(checkgroup)
    if rules == None:
        return []

    try:
        # checks without an item
        if item == None and checkgroup not in service_rule_groups:
            return host_extra_conf(host, rules)
        else: # checks with an item need service-specific rules
            return service_extra_conf(host, item, rules)
    except MKGeneralException, e:
        raise MKGeneralException(str(e) + " (on host %s, checktype %s)" % (host, checktype))


def get_management_board_precedence(check_plugin_name):
    mgmt_board = check_info[check_plugin_name]["management_board"]
    if mgmt_board is None:
        return check_api_utils.HOST_PRECEDENCE
    else:
        return mgmt_board


# TODO: Better move this function to py
def do_status_data_inventory_for(hostname):
    rules = active_checks.get('cmk_inv')
    if rules is None:
        return False

    # 'host_extra_conf' is already cached thus we can
    # use it after every check cycle.
    entries = host_extra_conf(hostname, rules)

    if not entries:
        return False # No matching rule -> disable

    # Convert legacy rules to current dict format (just like the valuespec)
    params = {} if entries[0] is None else entries[0]

    return params.get('status_data_inventory', False)


def filter_by_management_board(hostname, found_check_plugin_names,
                               for_mgmt_board, for_discovery=False):
    # #1 SNMP host with MGMT board
    #    MGMT board:
    #        SNMP management board precedence: mgmt_prec_check
    #        SNMP management board only:       mgmt_only_check
    #        SNMP host precedence:             host_prec_check
    #        SNMP host only:                   host_only_check
    #        SNMP Finally found check plugins: mgmt_only_check mgmt_prec_check
    #    HOST:
    #        SNMP management board precedence: mgmt_prec_check
    #        SNMP management board only:       mgmt_only_check
    #        SNMP host precedence:             host_prec_check
    #        SNMP host only:                   host_only_check
    #        SNMP Finally found check plugins: host_prec_check
    #    => Discovery:
    #        1 host_prec_snmp_uptime
    #        1 mgmt_only_snmp_uptime
    #        1 mgmt_prec_snmp_uptime
    #
    # #2 SNMP host without MGMT board
    #    HOST:
    #        SNMP management board precedence: mgmt_prec_check
    #        SNMP management board only:       mgmt_only_check
    #        SNMP host precedence:             host_prec_check
    #        SNMP host only:                   host_only_check
    #        SNMP Finally found check plugins: host_only_check host_prec_check mgmt_prec_check
    #    => Discovery:
    #        1 host_only_snmp_uptime
    #        1 host_prec_snmp_uptime
    #        1 mgmt_prec_snmp_uptime

    final_collection = set()
    mgmt_precedence = set()
    host_precedence = set()
    mgmt_only = set()
    host_only = set()
    for check_plugin_name in found_check_plugin_names:
        mgmt_board = get_management_board_precedence(check_plugin_name)
        if mgmt_board == check_api_utils.MGMT_PRECEDENCE:
            mgmt_precedence.add(check_plugin_name)

        elif mgmt_board == check_api_utils.HOST_PRECEDENCE:
            host_precedence.add(check_plugin_name)

        elif mgmt_board == check_api_utils.MGMT_ONLY:
            mgmt_only.add(check_plugin_name)

        elif mgmt_board == check_api_utils.HOST_ONLY:
            host_only.add(check_plugin_name)

    has_mgmt_board = has_management_board(hostname)
    if for_mgmt_board:
        final_collection.update(mgmt_precedence)
        final_collection.update(mgmt_only)
        if not for_discovery and not is_snmp_host(hostname):
            # Compatibility: in CMK version 1.4.0 if a TCP host has configured
            # a SNMP management board then SNMP checks (non-"SNMP management board"-checks)
            # were discovered. During checking we do not change that behaviour.
            # Then an upgrade to >=1.5.0 is done.
            # After a rediscovery the non-"SNMP management board"-checks are vanished and
            # "SNMP management board"-checks are discovered.
            final_collection.update(host_precedence)
    else:
        final_collection.update(host_precedence)
        if not has_mgmt_board:
            final_collection.update(mgmt_precedence)

    if not (has_mgmt_board or for_mgmt_board):
        final_collection.update(host_only)

    return final_collection

cmk_base.cleanup.register_cleanup(check_api_utils.reset_hostname)
