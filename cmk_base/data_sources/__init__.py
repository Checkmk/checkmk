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
# raw data:      The raw unparsed data produced by the data source (_execute()).
#                For the agent this is the whole byte string received from the
#                agent. For SNMP this is a python data structure containing
#                all OID/values received from SNMP.
# host_sections: A wrapper object for the "sections" and other information like
#                cache info and piggyback lines that is used to process the
#                data within Check_MK.

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
import cmk_base.piggyback
import cmk_base.snmp as snmp
import cmk_base.core_config as core_config
from cmk_base.exceptions import MKSkipCheck, MKAgentError, MKDataSourceError, MKSNMPError, \
                                MKParseFunctionError, MKTimeout

from .snmp import SNMPDataSource, SNMPManagementBoardDataSource
from .tcp import TCPDataSource
from .piggyback import PiggyBackDataSource
from .programs import DSProgramDataSource, SpecialAgentDataSource
from .host_sections import HostSections

# TODO: Refactor this to the DataSources() object. To be able to do this we need to refactor
# several call sites first to work only with a single DataSources() object during processing
# of a call.
g_data_source_errors = {}

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
# TODO: Move this to the sources? Or is it another layer on top of the sources? Refactor this to
#       a dedicated object HostSections().

def get_host_sections(sources, hostname, ipaddress, max_cachefile_age=None):
    """Generic function to gather ALL host info data for any host (hosts, nodes, clusters) in
    Check_MK.

    Returns a dictionary object of already parsed HostSections() constructs for each related host.
    For single hosts it's just a single entry in the dictionary. For cluster hosts it contains one
    HostSections() entry for each related node.

    Communication errors are not raised through by this functions. All agent related errors are
    stored in the g_data_source_errors construct which can be accessed by the caller to get
    the errors of each data source. The caller should do this, e.g. using
    data_sources.get_data_source_errors_of_host() and transparently display the errors to the
    users.
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
        abstract.DataSource.set_may_use_cache_file()

    # Special agents can produce data for the same check_plugin_name on the same host, in this case
    # the section lines need to be extended
    multi_host_sections = {}
    for this_hostname, this_ipaddress, this_max_cachfile_age in hosts:
        # In case a max_cachefile_age is given with the function call, always use this one
        # instead of the host individual one. This is only used in discovery mode.
        if max_cachefile_age is not None:
            sources.set_max_cachefile_age(max_cachefile_age)
        else:
            sources.set_max_cachefile_age(this_max_cachfile_age)

        for source in sources.get_data_sources():
            host_sections_from_source = source.run(this_hostname, this_ipaddress)

            host_sections = multi_host_sections.setdefault((this_hostname, this_ipaddress), HostSections())
            host_sections.update(host_sections_from_source)

        # Store piggyback information received from all sources of this host. This
        # also implies a removal of piggyback files received during previous calls.
        cmk_base.piggyback.store_piggyback_raw_data(this_hostname, host_sections.piggybacked_lines)

    return multi_host_sections


def get_section_content_for_check(multi_host_sections, hostname, ipaddress, check_plugin_name, for_discovery):
    """Prepares the section_content construct for a Check_MK check on ANY host

    The section_content construct is then handed over to the check, inventory or
    discovery functions for doing their work.

    If the host is a cluster, the sections from all its nodes is merged together
    here. Optionally the node info is added to the nodes section content.

    It receives the whole multi_host_sections data and cares about these aspects:

    a) Extract the section_content for the given check_plugin_name
    b) Adds node_info to the section_content (if check asks for this)
    c) Applies the parse function (if check has some)
    d) Adds extra_sections (if check asks for this)
       and also applies node_info and extra_section handling to this

    It can return an section_content construct or None when there is no section content
    for this check available.
    """
    section_name = checks.section_name_of(check_plugin_name)

    # First abstract cluster / non cluster hosts
    host_entries = []
    nodes = config.nodes_of(hostname)
    if nodes != None:
        for node_hostname in nodes:
            host_entries.append((node_hostname, ip_lookup.lookup_ip_address(node_hostname)))
    else:
        host_entries.append((hostname, ipaddress))

    # Now get the section_content from the required hosts and merge them together to
    # a single section_content. For each host optionally add the node info.
    section_content = None
    for host_entry in host_entries:
        try:
            host_section_content = multi_host_sections[host_entry].sections[section_name]
        except KeyError:
            continue

        host_section_content = _update_with_node_column(host_section_content,
                                      check_plugin_name, host_entry[0], for_discovery)

        if section_content is None:
            section_content = []

        section_content += host_section_content

    if section_content is None:
        return None

    assert type(section_content) == list

    section_content = _update_with_parse_function(section_content, section_name)
    section_content = _update_with_extra_sections(section_content, multi_host_sections,
                                    hostname, ipaddress, section_name, for_discovery)

    return section_content


def _update_with_node_column(section_content, check_plugin_name, hostname, for_discovery):
    """Add cluster node information to the section content

    If the check want's the node column, we add an additional column (as the first column) with the
    name of the node or None in case of non-clustered nodes.

    Whether or not a node info is requested by a check is not a property of the agent section. Each
    check/subcheck can define the requirement on it's own.

    When called for the discovery, the node name is always set to "None". During the discovery of
    services we behave like a non-cluster because we don't know whether or not the service will
    be added to the cluster or the node. This decision is made later during creation of the
    configuation. This means that the discovery function must work independent from the node info.
    """
    if check_plugin_name not in checks.check_info or not checks.check_info[check_plugin_name]["node_info"]:
        return section_content # unknown check_plugin_name or does not want node info -> do nothing

    if for_discovery:
        node_name = None
    else:
        node_name = hostname

    return _add_node_column(section_content, node_name)


def _add_node_column(section_content, nodename):
    new_section_content = []
    for line in section_content:
        if len(line) > 0 and type(line[0]) == list:
            new_entry = []
            for entry in line:
                new_entry.append([ nodename ] + entry)
            new_section_content.append(new_entry)
        else:
            new_section_content.append([ nodename ] + line)
    return new_section_content


def _update_with_extra_sections(section_content, multi_host_sections, hostname, ipaddress,
                                section_name, for_discovery):
    """Adds additional agent sections to the section_content the check receives.

    Please note that this is not a check/subcheck individual setting. This option is related
    to the agent section.
    """
    if section_name not in checks.check_info or not checks.check_info[section_name]["extra_sections"]:
        return section_content

    # In case of extra_sections the existing info is wrapped into a new list to which all
    # extra sections are appended
    section_content = [ section_content ]
    for extra_section_name in checks.check_info[section_name]["extra_sections"]:
        section_content.append(get_section_content_for_check(multi_host_sections, hostname, ipaddress,
                                                             extra_section_name, for_discovery))

    return section_content


def _update_with_parse_function(section_content, section_name):
    """Transform the section_content using the defined parse functions.

    Some checks define a parse function that is used to transform the section_content
    somehow. It is applied by this function.

    Please note that this is not a check/subcheck individual setting. This option is related
    to the agent section.

    All exceptions raised by the parse function will be catched and re-raised as
    MKParseFunctionError() exceptions."""

    if section_name not in checks.check_info:
        return section_content

    parse_function = checks.check_info[section_name]["parse_function"]
    if not parse_function:
        return section_content

    try:
        item_state.set_item_state_prefix(section_name, None)
        return parse_function(section_content)
    except Exception:
        if cmk.debug.enabled():
            raise
        raise MKParseFunctionError(*sys.exc_info())

    return section_content


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
        self._initialize_data_sources()


    def _initialize_data_sources(self):
        self._sources = {}

        self._initialize_agent_based_data_sources()
        self._initialize_snmp_data_sources()
        self._initialize_management_board_data_sources()


    def _initialize_agent_based_data_sources(self):
        if config.is_all_agents_host(self._hostname):
            source = self._get_agent_data_source(ignore_special_agents=True)
            source.set_main_agent_data_source()
            self._add_source(source)

            self._add_sources(self._get_special_agent_data_sources())

        elif config.is_all_special_agents_host(self._hostname):
            self._add_sources(self._get_special_agent_data_sources())

        elif config.is_tcp_host(self._hostname):
            source = self._get_agent_data_source()
            source.set_main_agent_data_source()
            self._add_source(source)

        self._add_source(PiggyBackDataSource())


    def _initialize_snmp_data_sources(self):
        if config.is_snmp_host(self._hostname):
            self._add_source(SNMPDataSource())


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

        elif config.is_tcp_host(self._hostname):
            return "Contact either Check_MK Agent or use a single special agent"

        else:
            return "No agent"


    def _get_agent_data_source(self, ignore_special_agents=False):
        if not ignore_special_agents:
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


    def get_check_plugin_names(self, hostname, ipaddress):
        """Returns the list of check types the caller may execute on the sections produced
        by these sources.

        Either returns a list of enforced check types (if set before) or ask each individual
        data source for it's supported check types and return a list of these types.
        """
        check_plugin_names = set()

        for source in self._sources.values():
            check_plugin_names.update(source.get_check_plugin_names(hostname, ipaddress))

        return list(check_plugin_names)


    def enforce_check_plugin_names(self, check_plugin_names):
        for source in self.get_data_sources():
            source.enforce_check_plugin_names(check_plugin_names)


    def get_data_sources(self):
        return sorted(self._sources.values(), key=lambda s: s.id())


    def set_max_cachefile_age(self, max_cachefile_age):
        for source in self.get_data_sources():
            source.set_max_cachefile_age(max_cachefile_age)


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
