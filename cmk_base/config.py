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
import marshal

import cmk.paths

import cmk_base
import cmk_base.console as console
import cmk_base.default_config as default_config
import cmk_base.rulesets as rulesets

from cmk_base.default_config import *

def get_variable_names():
    """Provides the list of all known configuration variables."""
    return [ k for k in default_config.__dict__.keys() if k[0] != "_" ]


def get_default_config():
    """Provides a dictionary containing the Check_MK default configuration"""
    cfg = {}
    for key in get_variable_names():
        cfg[key] = getattr(default_config, key)
    return cfg


def load_default_config():
    globals().update(get_default_config())


def register(name, default_value):
    """Register a new configuration variable within Check_MK base."""
    setattr(default_config, name, default_value)


# Add configuration variables registered by checks to config module
def add_check_variables(check_variables):
    default_config.__dict__.update(check_variables)


# Load user configured values of check related configuration variables
# into the check module to make it available during checking.
#
# In the same step we remove the check related configuration settings from the
# config module because they are not needed there anymore.
def set_check_variables_for_checks():
    import cmk_base.checks
    global_dict = globals()
    for varname in cmk_base.checks.check_variable_names():
        setattr(cmk_base.checks, varname, global_dict.pop(varname))
        delattr(default_config, varname)


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

# TODO: Use get_variable_names()
vars_before_config = set([])


def load(with_conf_d=True, validate_hosts=True):
    import cmk_base.checks
    global vars_before_config, checks

    load_default_config()

    # Initialize dictionary-type default levels variables
    for check in cmk_base.checks.check_info.values():
        def_var = check.get("default_levels_variable")
        if def_var:
            globals()[def_var] = {}

    # Create list of all files to be included
    if with_conf_d:
        list_of_files = reduce(lambda a,b: a+b,
           [ [ "%s/%s" % (d, f) for f in fs if f.endswith(".mk")]
             for d, _unused_sb, fs in os.walk(cmk.paths.check_mk_config_dir) ], [])
        # list_of_files.sort()
        list_of_files.sort(cmp = cmp_config_paths)
        list_of_files = [ cmk.paths.main_config_file ] + list_of_files
    else:
        list_of_files = [ cmk.paths.main_config_file ]

    for path in [ cmk.paths.final_config_file, cmk.paths.local_config_file ]:
        if os.path.exists(path):
            list_of_files.append(path)

    global_dict = globals()
    global_dict.update({
        "FILE_PATH"    : None,
        "FOLDER_PATH"  : None,
        "ALL_HOSTS"    : rulesets.ALL_HOSTS,
        "ALL_SERVICES" : rulesets.ALL_SERVICES,
    })

    vars_before_config = all_nonfunction_vars()
    for _f in list_of_files:
        # Hack: during parent scan mode we must not read in old version of parents.mk!
        # TODO: Hand this over via parameter or simmilar
        if '--scan-parents' in sys.argv and _f.endswith("/parents.mk"):
            continue
        try:
            _old_all_hosts = all_hosts[:]
            _old_clusters = clusters.keys()
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
            marks_hosts_with_path(_old_all_hosts, all_hosts, _f)
            marks_hosts_with_path(_old_clusters, clusters.keys(), _f)
        except Exception, e:
            if cmk.debug.enabled():
                raise
            elif sys.stdout.isatty():
                console.error("Cannot read in configuration file %s: %s", _f, e)
                sys.exit(1)


    # Cleanup global helper vars
    # TODO: Get list from above
    for helper_var in [ "FILE_PATH", "FOLDER_PATH", "ALL_HOSTS" ]:
        del global_dict[helper_var]

    initialize_config_caches()

    global service_service_levels, host_service_levels
    service_service_levels = extra_service_conf.get("_ec_sl", [])
    host_service_levels = extra_host_conf.get("_ec_sl", [])

    if validate_hosts:
        duplicates = duplicate_hosts()
        if duplicates:
            # TODO: Raise an exception
            console.error("Error in configuration: duplicate hosts: %s\n",
                                                    ", ".join(duplicates))
            sys.exit(3)

    # Add WATO-configured explicit checks to (possibly empty) checks
    # statically defined in checks.
    static = []
    for entries in static_checks.values():
        for entry in entries:
            entry, rule_options = rulesets.get_rule_options(entry)
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
                def_levels_varname = cmk_base.checks.check_info[checktype].get("default_levels_variable")
                if def_levels_varname:
                    for key, value in cmk_base.checks.factory_settings.get(def_levels_varname, {}).items():
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

    initialize_check_caches()
    set_check_variables_for_checks()

    # Check for invalid configuration variables
    vars_after_config = all_nonfunction_vars()
    ignored_variables = set(['vars_before_config', 'parts',
                             'seen_hostnames',
                             'taggedhost' ,'hostname',
                             'service_service_levels',
                             'host_service_levels'])
    errors = 0
    for name in vars_after_config:
        if name not in ignored_variables and name not in vars_before_config:
            console.error("Invalid configuration variable '%s'\n", name)
            errors += 1

    # Special handling for certain deprecated variables
    if type(snmp_communities) == dict:
        console.error("ERROR: snmp_communities cannot be a dict any more.\n")
        errors += 1

    if errors > 0:
        console.error("--> Found %d invalid variables\n" % errors)
        console.error("If you use own helper variables, please prefix them with _.\n")
        # TODO: Raise an exception
        sys.exit(1)


def initialize_config_caches():
    collect_hosttags()


def initialize_check_caches():
    single_host_checks = cmk_base.config_cache.get_dict("single_host_checks")
    multi_host_checks  = cmk_base.config_cache.get_list("multi_host_checks")

    for entry in checks:
        if len(entry) == 4 and type(entry[0]) == str:
            single_host_checks.setdefault(entry[0], []).append(entry)
        else:
            multi_host_checks.append(entry)


def marks_hosts_with_path(old, all, filename):
    if not filename.startswith(cmk.paths.check_mk_config_dir):
        return
    path = filename[len(cmk.paths.check_mk_config_dir):]
    old = set([ o.split("|", 1)[0] for o in old ])
    all = set([ a.split("|", 1)[0] for a in all ])
    for host in all:
        if host not in old:
            host_paths[host] = path


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
def cmp_config_paths(a, b):
    pa = a.split('/')
    pb = b.split('/')
    return cmp(pa[:-1], pb[:-1]) or \
           cmp(len(pa), len(pb)) or \
           cmp(pa, pb)


def load_packed_config():
    filepath = cmk.paths.var_dir + "/core/helper_config.mk"
    exec(marshal.load(open(filepath)), globals())



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
        result = map(lambda h: h.split('|', 1)[0], tagged_hostlist)
        cache[cache_id] = result
        return result


def tags_of_host(hostname):
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
    if cache.is_empty():
        cache.update(all_active_realhosts(), all_active_clusters())
    return cache


# Returns a set of all host names to be handled by this site
# hosts of other sitest or disabled hosts are excluded
def all_active_realhosts():
    active_realhosts = cmk_base.config_cache.get_set("active_realhosts")

    if active_realhosts.is_empty():
        active_realhosts.update(filter_active_hosts(all_configured_realhosts()))

    return active_realhosts


# Returns a set of all cluster host names to be handled by
# this site hosts of other sitest or disabled hosts are excluded
def all_active_clusters():
    active_clusters = cmk_base.config_cache.get_set("active_clusters")

    if active_clusters.is_empty():
        active_clusters.update(filter_active_hosts(all_configured_clusters()))

    return active_clusters


# Returns a set of all hosts, regardless if currently
# disabled or monitored on a remote site.
def all_configured_hosts():
    cache = cmk_base.config_cache.get_set("all_configured_hosts")
    if cache.is_empty():
        cache.update(all_configured_realhosts(), all_configured_clusters())
    return cache


# Returns a set of all host names, regardless if currently
# disabled or monitored on a remote site. Does not return
# cluster hosts.
def all_configured_realhosts():
    cache = cmk_base.config_cache.get_set("all_configured_realhosts")
    if cache.is_empty():
        cache.update(strip_tags(all_hosts))
    return cache


# Returns a set of all cluster names, regardless if currently
# disabled or monitored on a remote site. Does not return
# normal hosts.
def all_configured_clusters():
    cache = cmk_base.config_cache.get_set("all_configured_clusters")
    if cache.is_empty():
        cache.update(strip_tags(clusters.keys()))
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

    for hostname in config.all_active_hosts_with_duplicates():
        if hostname in seen_hostnames:
            duplicates.add(hostname)
        else:
            seen_hostnames.add(hostname)

    return sorted(list(duplicates))

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
    aliases = rulesets.host_extra_conf(hostname, extra_host_conf.get("alias", []))
    if len(aliases) == 0:
        if fallback:
            return fallback
        else:
            return hostname
    else:
        return aliases[0]


def parents_of(hostname):
    par = rulesets.host_extra_conf(hostname, parents)
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
    if cache.is_empty():
        for cluster, hosts in clusters.items():
            clustername = cluster.split('|', 1)[0]
            for name in hosts:
                cache.setdefault(name, []).append(clustername)

    return cache.get(hostname, [])


#
# Agent type
#

def is_tcp_host(hostname):
    return rulesets.in_binary_hostlist(hostname, tcp_hosts)


def is_snmp_host(hostname):
    return rulesets.in_binary_hostlist(hostname, snmp_hosts)


def is_ping_host(hostname):
    import cmk_base.piggyback as piggyback
    return not is_snmp_host(hostname) \
       and not is_tcp_host(hostname) \
       and not piggyback.has_piggyback_info(hostname) \
       and not has_management_board(hostname)


def is_dual_host(hostname):
    return is_tcp_host(hostname) and is_snmp_host(hostname)


#
# IPv4/IPv6
#

def is_ipv6_primary(hostname):
    dual_stack_host = is_ipv4v6_host(hostname)
    return (not dual_stack_host and is_ipv6_host(hostname)) \
            or (dual_stack_host and rulesets.host_extra_conf(hostname, primary_address_family) == "ipv6")


def is_ipv4v6_host(hostname):
    tags = tags_of_host(hostname)
    return "ip-v6" in tags and "ip-v4" in tags


def is_ipv6_host(hostname):
    return "ip-v6" in tags_of_host(hostname)


def is_ipv4_host(hostname):
    # Either explicit IPv4 or implicit (when host is not an IPv6 host)
    return "ip-v4" in tags_of_host(hostname) or "ip-v6" not in tags_of_host(hostname)


#
# Management board
#

def has_management_board(hostname):
    return "management_protocol" in host_attributes.get(hostname, {})


def management_address(hostname):
    if 'management_address' in host_attributes.get(hostname, {}):
        return host_attributes[hostname]['management_address']
    else:
        return ipaddresses.get(hostname)


def management_protocol(hostname):
    return host_attributes[hostname]['management_protocol']


#
# Agent communication
#

def agent_port_of(hostname):
    ports = rulesets.host_extra_conf(hostname, agent_ports)
    if len(ports) == 0:
        return agent_port
    else:
        return ports[0]


def agent_encryption_of(hostname):
    settings = rulesets.host_extra_conf(hostname, agent_encryption)
    if settings:
        return settings[0]
    else:
        return {'use_regular': 'disabled',
                'use_realtime': 'enforce'}


def agent_target_version(hostname):
    agent_target_versions = rulesets.host_extra_conf(hostname, check_mk_agent_target_versions)
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
    # TODO: this works under the assumption that we can't have the management
    #  board and the host itself queried through snmp.
    #  The alternative is a lengthy and errorprone refactoring of the whole check-
    #  call hierarchy to get the credentials passed around.
    if has_management_board(hostname)\
            and management_protocol(hostname) == "snmp":
        return host_attributes.get(hostname, {}).get("management_snmp_community", "public")

    try:
        return explicit_snmp_communities[hostname]
    except KeyError:
        pass

    communities = rulesets.host_extra_conf(hostname, snmp_communities)
    if len(communities) > 0:
        return communities[0]

    # nothing configured for this host -> use default
    return snmp_default_community


def snmp_character_encoding_of(hostname):
    entries = rulesets.host_extra_conf(hostname, snmp_character_encodings)
    if len(entries) > 0:
        return entries[0]


def snmp_timing_of(hostname):
    timing = rulesets.host_extra_conf(hostname, snmp_timing)
    if len(timing) > 0:
        return timing[0]
    else:
        return {}


def snmpv3_contexts_of(hostname):
    return rulesets.host_extra_conf(hostname, snmpv3_contexts)


def oid_range_limits_of(hostname):
    return rulesets.host_extra_conf(hostname, snmp_limit_oid_range)


def snmp_port_of(hostname):
    ports = rulesets.host_extra_conf(hostname, snmp_ports)
    if len(ports) == 0:
        return None # do not specify a port, use default
    else:
        return ports[0]


def is_snmpv3_host(hostname):
    return type(snmp_credentials_of(hostname)) == tuple


def is_bulkwalk_host(hostname):
    if bulkwalk_hosts:
        return rulesets.in_binary_hostlist(hostname, bulkwalk_hosts)
    else:
        return False


def is_snmpv2c_host(hostname):
    return is_bulkwalk_host(hostname) or \
        rulesets.in_binary_hostlist(hostname, snmpv2c_hosts)


def is_usewalk_host(hostname):
    return rulesets.in_binary_hostlist(hostname, usewalk_hosts)


def is_inline_snmp_host(hostname):
    # TODO: Better use "inline_snmp" once we have moved the code to an own module
    has_inline_snmp = "netsnmp" in sys.modules
    return has_inline_snmp and use_inline_snmp \
           and not rulesets.in_binary_hostlist(hostname, non_inline_snmp_hosts)


#
# Groups
#

def hostgroups_of(hostname):
    return rulesets.host_extra_conf(hostname, host_groups)


def summary_hostgroups_of(hostname):
    return rulesets.host_extra_conf(hostname, summary_host_groups)


def contactgroups_of(hostname):
    cgrs = []

    # host_contactgroups may take single values as well as
    # lists as item value. Of all list entries only the first
    # one is used. The single-contact-groups entries are all
    # recognized.
    first_list = True
    for entry in rulesets.host_extra_conf(hostname, host_contactgroups):
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

def get_piggyback_translation(hostname):
    """Get a dict that specifies the actions to be done during the hostname translation"""
    rules = rulesets.host_extra_conf(hostname, piggyback_translation)
    translations = {}
    for rule in rules[::-1]:
        translations.update(rule)
    return translations


def exit_code_spec(hostname):
    spec = {}
    specs = rulesets.host_extra_conf(hostname, check_mk_exit_status)
    for entry in specs[::-1]:
        spec.update(entry)
    return spec


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
    return monitoring_core == "cmc"


def decode_incoming_string(s, encoding="utf-8"):
    try:
        return s.decode(encoding)
    except:
        return s.decode(fallback_agent_output_encoding)
