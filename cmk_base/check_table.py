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

"""Code for computing the table of checks of hosts."""

from cmk.regex import regex
from cmk.exceptions import MKGeneralException

import cmk_base
import cmk_base.config as config
import cmk_base.checks as checks
import cmk_base.rulesets as rulesets
import cmk_base.piggyback as piggyback
import cmk_base.item_state as item_state


# Returns check table for a specific host
# Format: (checkname, item) -> (params, description)
def get_check_table(hostname, remove_duplicates=False, use_cache=True, world='config', skip_autochecks=False):
    import cmk_base.discovery as discovery

    if config.is_ping_host(hostname):
        skip_autochecks = True

    # speed up multiple lookup of same host
    check_table_cache = cmk_base.config_cache.get_dict("check_tables")
    if not skip_autochecks and use_cache and hostname in check_table_cache:
        if remove_duplicates and config.is_dual_host(hostname):
            return _remove_duplicate_checks(check_table_cache[hostname])
        else:
            return check_table_cache[hostname]

    check_table = {}

    single_host_checks = cmk_base.config_cache.get_dict("single_host_checks")
    multi_host_checks  = cmk_base.config_cache.get_list("multi_host_checks")

    hosttags = config.tags_of_host(hostname)

    # Just a local cache and its function
    is_checkname_valid_cache = {}
    def is_checkname_valid(checkname):
        the_id = (hostname, checkname)
        if the_id in is_checkname_valid_cache:
            return is_checkname_valid_cache[the_id]

        passed = True
        # Skip SNMP checks for non SNMP hosts (might have been discovered before with other
        # agent setting. Remove them without rediscovery). Same for agent based checks.
        if not config.is_snmp_host(hostname) and checks.is_snmp_check(checkname) and \
           (not config.has_management_board(hostname) or config.management_protocol(hostname) != "snmp"):
                passed = False
        if not config.is_tcp_host(hostname) and not piggyback.has_piggyback_info(hostname) \
           and checks.is_tcp_check(checkname):
            passed = False
        is_checkname_valid_cache[the_id] = passed
        return passed


    def handle_entry(entry):
        num_elements = len(entry)
        if num_elements == 3: # from autochecks
            hostlist = hostname
            checkname, item, params = entry
            tags = []
        elif num_elements == 4:
            hostlist, checkname, item, params = entry
            tags = []
        elif num_elements == 5:
            tags, hostlist, checkname, item, params = entry
            if type(tags) != list:
                raise MKGeneralException("Invalid entry '%r' in check table. First entry must be list of host tags." %
                                         (entry, ))

        else:
            raise MKGeneralException("Invalid entry '%r' in check table. It has %d entries, but must have 4 or 5." %
                                     (entry, len(entry)))

        # hostlist list might be:
        # 1. a plain hostname (string)
        # 2. a list of hostnames (list of strings)
        # Hostnames may be tagged. Tags are removed.
        # In autochecks there are always single untagged hostnames. We optimize for that.
        if type(hostlist) == str:
            if hostlist != hostname:
                return # optimize most common case: hostname mismatch
            hostlist = [ hostlist ]
        elif type(hostlist[0]) == str:
            pass # regular case: list of hostnames
        elif hostlist != []:
            raise MKGeneralException("Invalid entry '%r' in check table. Must be single hostname "
                                     "or list of hostnames" % hostlist)

        if not is_checkname_valid(checkname):
            return

        if rulesets.hosttags_match_taglist(hosttags, tags) and \
               rulesets.in_extraconf_hostlist(hostlist, hostname):
            descr = config.service_description(hostname, checkname, item)
            if config.service_ignored(hostname, checkname, descr):
                return
            if hostname != config.host_of_clustered_service(hostname, descr):
                return
            deps  = service_deps(hostname, descr)
            check_table[(checkname, item)] = (params, descr, deps)

    # Now process all entries that are specific to the host
    # in search (single host) or that might match the host.
    if not skip_autochecks:
        for entry in discovery.read_autochecks_of(hostname, world):
            handle_entry(entry)

    for entry in single_host_checks.get(hostname, []):
        handle_entry(entry)

    for entry in multi_host_checks:
        handle_entry(entry)

    # Now add checks a cluster might receive from its nodes
    if config.is_cluster(hostname):
        single_host_checks = cmk_base.config_cache.get_dict("single_host_checks")

        for node in config.nodes_of(hostname):
            node_checks = single_host_checks.get(node, [])
            if not skip_autochecks:
                node_checks = node_checks + discovery.read_autochecks_of(node, world)
            for entry in node_checks:
                if len(entry) == 4:
                    entry = entry[1:] # drop hostname from single_host_checks
                checkname, item, params = entry
                descr = config.service_description(node, checkname, item)
                if hostname == config.host_of_clustered_service(node, descr):
                    cluster_params = checks.compute_check_parameters(hostname, checkname, item, params)
                    handle_entry((hostname, checkname, item, cluster_params))


    # Remove dependencies to non-existing services
    all_descr = set([ descr for ((checkname, item), (params, descr, deps)) in check_table.items() ])
    for (checkname, item), (params, descr, deps) in check_table.items():
        deeps = deps[:]
        del deps[:]
        for d in deeps:
            if d in all_descr:
                deps.append(d)

    if not skip_autochecks and use_cache:
        check_table_cache[hostname] = check_table

    if remove_duplicates:
        return _remove_duplicate_checks(check_table)
    else:
        return check_table


def get_precompiled_check_table(hostname, remove_duplicates=True, world="config"):
    host_checks = get_sorted_check_table(hostname, remove_duplicates, world)
    precomp_table = []
    for check_type, item, params, description, _unused_deps in host_checks:
        # make these globals available to the precompile function
        checks.set_service_description(description)
        item_state.set_item_state_prefix(check_type, item)

        params = get_precompiled_check_parameters(hostname, item, params, check_type)
        precomp_table.append((check_type, item, params, description)) # deps not needed while checking
    return precomp_table


def get_precompiled_check_parameters(hostname, item, params, check_type):
    precomp_func = checks.precompile_params.get(check_type)
    if precomp_func:
        return precomp_func(hostname, item, params)
    else:
        return params


# Return a list of services this services depends upon
# TODO: Make this use the generic "rulesets" functions
# TODO: Is this needed here? Investigate for what this is used for
def service_deps(hostname, servicedesc):
    deps = []
    for entry in config.service_dependencies:
        entry, rule_options = rulesets.get_rule_options(entry)
        if rule_options.get("disabled"):
            continue

        if len(entry) == 3:
            depname, hostlist, patternlist = entry
            tags = []
        elif len(entry) == 4:
            depname, tags, hostlist, patternlist = entry
        else:
            raise MKGeneralException("Invalid entry '%r' in service dependencies: "
                                     "must have 3 or 4 entries" % entry)

        if rulesets.hosttags_match_taglist(config.tags_of_host(hostname), tags) and \
           rulesets.in_extraconf_hostlist(hostlist, hostname):
            for pattern in patternlist:
                matchobject = regex(pattern).search(servicedesc)
                if matchobject:
                    try:
                        item = matchobject.groups()[-1]
                        deps.append(depname % item)
                    except:
                        deps.append(depname)
    return deps


def _remove_duplicate_checks(check_table):
    have_with_tcp = {}
    have_with_snmp = {}
    without_duplicates = {}
    for key, value in check_table.iteritems():
        checkname = key[0]
        descr = value[1]
        if checks.is_snmp_check(checkname):
            if descr in have_with_tcp:
                continue
            have_with_snmp[descr] = key
        else:
            if descr in have_with_snmp:
                snmp_key = have_with_snmp[descr]
                del without_duplicates[snmp_key]
                del have_with_snmp[descr]
            have_with_tcp[descr] = key
        without_duplicates[key] = value
    return without_duplicates


# remove_duplicates: Automatically remove SNMP based checks
# if there already is a TCP based one with the same
# description. E.g: df vs hr_fs.
# TODO: Clean this up!
def get_sorted_check_table(hostname, remove_duplicates=False, world="config"):
    # Convert from dictionary into simple tuple list. Then sort
    # it according to the service dependencies.
    unsorted = [ (checkname, item, params, descr, deps)
                 for ((checkname, item), (params, descr, deps))
                 in get_check_table(hostname, remove_duplicates=remove_duplicates, world=world).items() ]
    def cmp(a, b):
        if a[3] < b[3]:
            return -1
        else:
            return 1
    unsorted.sort(key=lambda x: x[3])

    sorted = []
    while len(unsorted) > 0:
        unsorted_descrs = set([ entry[3] for entry in unsorted ])
        left = []
        at_least_one_hit = False
        for check in unsorted:
            deps_fulfilled = True
            for dep in check[4]: # deps
                if dep in unsorted_descrs:
                    deps_fulfilled = False
                    break
            if deps_fulfilled:
                sorted.append(check)
                at_least_one_hit = True
            else:
                left.append(check)
        if len(left) == 0:
            break
        if not at_least_one_hit:
            raise MKGeneralException("Cyclic service dependency of host %s. Problematic are: %s" %
                                     (hostname, ",".join(unsorted_descrs)))
        unsorted = left
    return sorted
