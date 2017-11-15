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

# Naming:
#
# raw data: The raw unparsed data produced by the data source (_execute()).
#           For the agent this is the whole byte string received from the
#           agent. For SNMP this is a python data structure containing
#           all OID/values received from SNMP.
# info:     The parsed raw data recevied from the data source (run()).
#           The transformation from the raw data is done by the
#           _convert_to_infos() method of the source.
# host_info A wrapper object for the "info" and other information like
#           cache info and piggyback lines that is used to process the
#           data within Check_MK.

import ast
import os
import signal
import socket
import subprocess
import sys
import time

import cmk.paths
import cmk.debug
from cmk.exceptions import MKGeneralException

import cmk_base
import cmk.store as store
import cmk_base.config as config
import cmk_base.rulesets as rulesets
import cmk_base.console as console
import cmk_base.checks as checks
import cmk_base.item_state as item_state
import cmk_base.ip_lookup as ip_lookup
import cmk_base.piggyback as piggyback
import cmk_base.snmp as snmp
import cmk_base.core_config as core_config
from cmk_base.exceptions import MKSkipCheck, MKAgentError, MKDataSourceError, MKSNMPError, \
                                MKParseFunctionError, MKTimeout

from .snmp import SNMPDataSource, SNMPManagementBoardDataSource
from .tcp import TCPDataSource
from .piggyback import PiggyBackDataSource
from .programs import DSProgramDataSource, SpecialAgentDataSource
from .host_info import HostInfo

g_data_source_errors         = {}

#.
#   .--Host infos----------------------------------------------------------.
#   |             _   _           _     _        __                        |
#   |            | | | | ___  ___| |_  (_)_ __  / _| ___  ___              |
#   |            | |_| |/ _ \/ __| __| | | '_ \| |_ / _ \/ __|             |
#   |            |  _  | (_) \__ \ |_  | | | | |  _| (_) \__ \             |
#   |            |_| |_|\___/|___/\__| |_|_| |_|_|  \___/|___/             |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Processing of host infos. This is the standard mechanism of Check_MK |
#   | to gather data for the monitoring (checking, inventory, discovery).  |
#   '----------------------------------------------------------------------'
# TODO: Move this to the sources? Or is it another layer on top of the sources?

def get_host_infos(sources, hostname, ipaddress, max_cachefile_age=None):
    """Generic function to gather ALL host info data for any host (hosts, nodes, clusters) in Check_MK.

    Returns a HostInfo() object of already parsed info constructs.

    Communication errors are not raised through by this functions. All agent related errors are
    stored in the g_data_source_errors construct which can be accessed by the caller to get
    the errors of each data source. The caller should do this, e.g. using
    data_sources.get_data_source_errors_of_host() and transparently display the errors to the users.
    """

    # First abstract clusters/nodes/hosts
    hosts = []
    nodes = config.nodes_of(hostname)
    if nodes is not None:
        for node_hostname in nodes:
            node_ipaddress = ip_lookup.lookup_ip_address(node_hostname)
            hosts.append((node_hostname, node_ipaddress, config.cluster_max_cachefile_age))
    else:
        hosts.append((hostname, ipaddress, config.check_max_cachefile_age))

    if nodes:
        import abstract
        abstract.DataSource.set_use_cachefile()

    # Special agents can produce data for the same check_type on the same host, in this case
    # the section lines need to be extended
    all_host_infos = {}
    for this_hostname, this_ipaddress, this_max_cachfile_age in hosts:
        # In case a max_cachefile_age is given with the function call, always use this one
        # instead of the host individual one. This is only used in discovery mode.
        if max_cachefile_age is not None:
            sources.set_max_cachefile_age(max_cachefile_age)
        else:
            sources.set_max_cachefile_age(this_max_cachfile_age)

        for source in sources.get_data_sources():
            host_info_of_source = source.run(this_hostname, this_ipaddress)

            host_info = all_host_infos.setdefault((this_hostname, this_ipaddress), HostInfo())
            host_info.update(host_info_of_source)

        # Store piggyback information received from all sources of this host. This
        # also implies a removal of piggyback files received during previous calls.
        piggyback.store_piggyback_raw_data(this_hostname, host_info.piggybacked_lines)

    return all_host_infos


def get_info_for_check(all_host_infos, hostname, ipaddress, check_type, for_discovery):
    """Prepares the info construct for a Check_MK check on ANY host

    The info construct is then handed over to the check or discovery functions
    for doing their work.

    If the host is a cluster, the information from all its nodes is used.

    It receives the whole all_host_infos data and cares about these aspects:

    a) Extract the section for the given check_type
    b) Adds node_info to the info (if check asks for this)
    c) Applies the parse function (if check has some)
    d) Adds extra_sections (if check asks for this)
       and also applies node_info and extra_section handling to this

    It can return an info construct or None when there is no info for this check
    available.
    """
    section_name = check_type.split('.')[0] # make e.g. 'lsi' from 'lsi.arrays'

    # First abstract cluster / non cluster hosts
    host_entries = []
    nodes = config.nodes_of(hostname)
    if nodes != None:
        for node_hostname in nodes:
            # TODO: why is for_discovery handled differently?
            node_name = node_hostname if not for_discovery else None
            host_entries.append(((node_hostname, ip_lookup.lookup_ip_address(node_hostname)), node_name))
    else:
        node_name = hostname if config.clusters_of(hostname) and not for_discovery else None
        host_entries.append(((hostname, ipaddress), node_name))

    # Now extract the sections of the relevant hosts and optionally add the node info
    info = None
    for host_entry, is_node in host_entries:
        try:
            info = all_host_infos[host_entry].info[section_name]
        except KeyError:
            continue

        info = _update_info_with_node_info(info, check_type, node_name)
        info = _update_info_with_parse_function(info, section_name)

    if info is None:
        return None

    # TODO: Is this correct? info!
    info = _update_info_with_extra_sections(info, all_host_infos, hostname, ipaddress, check_type, for_discovery)

    return info


# If the check want's the node info, we add an additional
# column (as the first column) with the name of the node
# or None (in case of non-clustered nodes). On problem arises,
# if we deal with subchecks. We assume that all subchecks
# have the same setting here. If not, let's raise an exception.
# TODO: Why not use the check_type instead of section_name? Inconsistent with node_info!
def _update_info_with_node_info(info, check_type, node_name):
    if check_type not in checks.check_info or not checks.check_info[check_type]["node_info"]:
        return info # unknown check_type or does not want node info -> do nothing

    return _add_nodeinfo(info, node_name)


def _add_nodeinfo(info, nodename):
    new_info = []
    for line in info:
        if len(line) > 0 and type(line[0]) == list:
            new_entry = []
            for entry in line:
                new_entry.append([ nodename ] + entry)
            new_info.append(new_entry)
        else:
            new_info.append([ nodename ] + line)
    return new_info


# TODO: Why not use the check_type instead of section_name? Inconsistent with node_info!
def _update_info_with_extra_sections(info, all_host_infos, hostname, ipaddress, section_name, for_discovery):
    if section_name not in checks.check_info or not checks.check_info[section_name]["extra_sections"]:
        return info

    # In case of extra_sections the existing info is wrapped into a new list to which all
    # extra sections are appended
    info = [ info ]
    for extra_section_name in checks.check_info[section_name]["extra_sections"]:
        info.append(get_info_for_check(all_host_infos, hostname, ipaddress, extra_section_name, for_discovery))

    return info


def _update_info_with_parse_function(info, section_name):
    """Some check types define a parse function that is used to transform the info
    somehow. It is applied by this function.

    All exceptions raised by the parse function will be catched and re-raised as
    MKParseFunctionError() exceptions."""

    if section_name not in checks.check_info:
        return info

    parse_function = checks.check_info[section_name]["parse_function"]
    if not parse_function:
        return info

    try:
        item_state.set_item_state_prefix(section_name, None)
        return parse_function(info)
    except Exception:
        if cmk.debug.enabled():
            raise
        raise MKParseFunctionError(*sys.exc_info())

    return info


#.
#   .--Data Sources--------------------------------------------------------.
#   |     ____        _          ____                                      |
#   |    |  _ \  __ _| |_ __ _  / ___|  ___  _   _ _ __ ___ ___  ___       |
#   |    | | | |/ _` | __/ _` | \___ \ / _ \| | | | '__/ __/ _ \/ __|      |
#   |    | |_| | (_| | || (_| |  ___) | (_) | |_| | | | (_|  __/\__ \      |
#   |    |____/ \__,_|\__\__,_| |____/ \___/ \__,_|_|  \___\___||___/      |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | The monitoring data is fetched using so called data sources.         |
#   '----------------------------------------------------------------------'

class DataSources(object):
    def __init__(self, hostname):
        super(DataSources, self).__init__()
        self._hostname = hostname
        self._enforced_check_types = None
        self._initialize_data_sources()


    def _initialize_data_sources(self):
        self._sources = {}

        if config.is_all_agents_host(self._hostname):
            self._add_source(self._get_agent_data_source())
            self._add_sources(self._get_special_agent_data_sources())

        elif config.is_all_special_agents_host(self._hostname):
            self._add_sources(self._get_special_agent_data_sources())

        else:
            self._add_source(self._get_agent_data_source())

        self._initialize_management_board_data_sources()
        self._initialize_piggyback_data_source()


    def _initialize_management_board_data_sources(self):
        if not config.has_management_board(self._hostname):
            return

        # this assumes all snmp checks belong to the management board if there is one with snmp
        # protocol. If at some point we support having both host and management board queried
        # through snmp we have to decide which check belongs where at discovery time and change
        # all data structures, including in the nagios interface...
        is_management_snmp = config.management_protocol(self._hostname) == "snmp"
        if not is_management_snmp:
            return

        self._add_source(SNMPManagementBoardDataSource())


    def _initialize_management_board_data_sources(self):
        self._add_source(PiggyBackDataSource())


    def _add_sources(self, sources):
        for source in sources:
            self._add_source(source)


    def _add_source(self, source):
        self._sources[source.id()] = source


    def describe_data_sources(self):
        if config.is_all_agents_host(self._hostname):
            return "Contact Check_MK Agent and use all enabled special agents"

        elif config.is_all_special_agents_host(self._hostname):
            return "Use all enabled special agents"

        else:
            return "Contact either Check_MK Agent or use a single special agent"


    def _get_agent_data_source(self):
        special_agents = self._get_special_agent_data_sources()
        if special_agents:
            return special_agents[0][1]

        programs = rulesets.host_extra_conf(self._hostname, config.datasource_programs)
        if programs:
            return DSProgramDataSource(programs[0])

        return TCPDataSource()


    def _get_special_agent_data_sources(self):
        special_agents = []

        # Previous to 1.5.0 it was not defined in which order the special agent
        # rules overwrite eachother. When multiple special agents were configured
        # for a single host a "random" one was picked (depending on the iteration
        # over config.special_agents.
        # We now sort the matching special agents by their name to at least get
        # a deterministic order of the special agents.
        for agentname, ruleset in sorted(config.special_agents.items()):
            params = rulesets.host_extra_conf(self._hostname, ruleset)
            if params:
                source = SpecialAgentDataSource(agentname, params[0])
                special_agents[source.id()] = source

        return special_agents


    def get_check_types(self, hostname, ipaddress):
        """Returns the list of check types the caller may execute on the host_infos produced
        by these sources.

        Either returns a list of enforced check types (if set before) or ask each individual
        data source for it's supported check types and return a list of these types.
        """
        if self._enforced_check_types is not None:
            return self._enforced_check_types

        check_types = set()

        for source in self._sources.values():
            check_types.update(source.get_check_types(hostname, ipaddress))

        return list(check_types)


    def enforce_check_types(self, check_types):
        self._enforced_check_types = list(set(check_types))


    def get_data_sources(self):
        return sorted(self._sources.values(), key=lambda s: s.id())


    def set_max_cachefile_age(self, max_cachefile_age):
        for source in self.get_data_sources():
            source.set_max_cachefile_age(max_cachefile_age)



#.
#   .--Use cachefile-------------------------------------------------------.
#   |       _   _                           _           __ _ _             |
#   |      | | | |___  ___    ___ __ _  ___| |__   ___ / _(_) | ___        |
#   |      | | | / __|/ _ \  / __/ _` |/ __| '_ \ / _ \ |_| | |/ _ \       |
#   |      | |_| \__ \  __/ | (_| (_| | (__| | | |  __/  _| | |  __/       |
#   |       \___/|___/\___|  \___\__,_|\___|_| |_|\___|_| |_|_|\___|       |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'
# FIXME TODO: Cleanup the whole caching crap

orig_check_max_cachefile_age     = None
orig_cluster_max_cachefile_age   = None
orig_inventory_max_cachefile_age = None

# TODO: Why 1000000000? Can't we really clean this up to a global variable which can
# be toggled to enforce the cache usage (if available). This way we would not need
# to store the original values of the different caches and modify them etc.
def enforce_using_agent_cache():
    global orig_check_max_cachefile_age, orig_cluster_max_cachefile_age, \
           orig_inventory_max_cachefile_age

    if config.check_max_cachefile_age != 1000000000:
        orig_check_max_cachefile_age     = config.check_max_cachefile_age
        orig_cluster_max_cachefile_age   = config.cluster_max_cachefile_age
        orig_inventory_max_cachefile_age = config.inventory_max_cachefile_age

    config.check_max_cachefile_age     = 1000000000
    config.cluster_max_cachefile_age   = 1000000000
    config.inventory_max_cachefile_age = 1000000000


def restore_original_agent_caching_usage():
    global orig_check_max_cachefile_age, orig_cluster_max_cachefile_age, \
           orig_inventory_max_cachefile_age

    if orig_check_max_cachefile_age != None:
        config.check_max_cachefile_age     = orig_check_max_cachefile_age
        config.cluster_max_cachefile_age   = orig_cluster_max_cachefile_age
        config.inventory_max_cachefile_age = orig_inventory_max_cachefile_age

        orig_check_max_cachefile_age     = None
        orig_cluster_max_cachefile_age   = None
        orig_inventory_max_cachefile_age = None



#.
#   .--Misc.---------------------------------------------------------------.
#   |                         __  __ _                                     |
#   |                        |  \/  (_)___  ___                            |
#   |                        | |\/| | / __|/ __|                           |
#   |                        | |  | | \__ \ (__ _                          |
#   |                        |_|  |_|_|___/\___(_)                         |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Different helper functions                                           |
#   '----------------------------------------------------------------------'

def cleanup_host_caches():
    g_data_source_errors.clear()


def add_data_source_error(hostname, ipaddress, data_source, e):
    g_data_source_errors.setdefault(hostname, {}).setdefault(data_source.name(hostname, ipaddress), []).append(e)


def has_data_source_errors(hostname, ipaddress, data_source):
    return bool(get_data_source_errors(hostname, ipaddress, data_source))


def get_data_source_errors(hostname, ipaddress, data_source):
    return g_data_source_errors.get(hostname, {}).get(data_source.name(hostname, ipaddress))


def get_data_source_errors_of_host(hostname, ipaddress):
    return g_data_source_errors.get(hostname, {})
