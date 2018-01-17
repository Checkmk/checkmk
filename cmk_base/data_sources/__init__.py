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

from .snmp import SNMPDataSource, SNMPManagementBoardDataSource
from .tcp import TCPDataSource
from .piggyback import PiggyBackDataSource
from .programs import DSProgramDataSource, SpecialAgentDataSource
from .host_sections import HostSections, MultiHostSections

# TODO: Refactor this to the DataSources() object. To be able to do this we need to refactor
# several call sites first to work only with a single DataSources() object during processing
# of a call.
g_data_source_errors = {}

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

        # Has currently no effect. The value possibly set during execution on the single data
        # sources is kept here in this object to return it later on
        self._enforced_check_plugin_names = None


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
                return special_agents[0]

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
                special_agents.append(SpecialAgentDataSource(agentname, params[0]))

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
        self._enforced_check_plugin_names = check_plugin_names
        for source in self.get_data_sources():
            source.enforce_check_plugin_names(check_plugin_names)


    def get_enforced_check_plugin_names(self):
        """Returns either the collection of enforced check plugin names (when they have been set before) or None"""
        return self._enforced_check_plugin_names


    def get_data_sources(self):
        # Always execute piggyback at the end
        return sorted(self._sources.values(), key=lambda s: (isinstance(s, PiggyBackDataSource), s.id()))


    def set_max_cachefile_age(self, max_cachefile_age):
        for source in self.get_data_sources():
            source.set_max_cachefile_age(max_cachefile_age)


    def get_host_sections(self, hostname, ipaddress, max_cachefile_age=None):
        """Gather ALL host info data for any host (hosts, nodes, clusters) in Check_MK.

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
        multi_host_sections = MultiHostSections()
        for this_hostname, this_ipaddress, this_max_cachfile_age in hosts:
            # In case a max_cachefile_age is given with the function call, always use this one
            # instead of the host individual one. This is only used in discovery mode.
            if max_cachefile_age is not None:
                self.set_max_cachefile_age(max_cachefile_age)
            else:
                self.set_max_cachefile_age(this_max_cachfile_age)

            for source in self.get_data_sources():
                host_sections_from_source = source.run(this_hostname, this_ipaddress)
                host_sections = multi_host_sections.add_or_get_host_sections(this_hostname, this_ipaddress)
                host_sections.update(host_sections_from_source)

            # Store piggyback information received from all sources of this host. This
            # also implies a removal of piggyback files received during previous calls.
            cmk_base.piggyback.store_piggyback_raw_data(this_hostname, host_sections.piggybacked_raw_data)

        return multi_host_sections




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
