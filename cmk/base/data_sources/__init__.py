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
from typing import (  # pylint: disable=unused-import
    cast, Iterable, TYPE_CHECKING, List, Dict, Optional, Set,
)

import cmk.utils.paths
import cmk.utils.debug
from cmk.utils.exceptions import MKGeneralException
import cmk.utils.store as store
import cmk.utils.piggyback

import cmk.base
import cmk.base.config as config
import cmk.base.console as console
import cmk.base.item_state as item_state
import cmk.base.ip_lookup as ip_lookup
import cmk.base.check_table as check_table
from cmk.base.check_utils import (  # pylint: disable=unused-import
    CheckPluginName,)
from cmk.base.utils import HostName, HostAddress  # pylint: disable=unused-import

from .snmp import SNMPDataSource, SNMPManagementBoardDataSource
from .ipmi import IPMIManagementBoardDataSource
from .tcp import TCPDataSource
from .piggyback import PiggyBackDataSource
from .programs import DSProgramDataSource, SpecialAgentDataSource
from .host_sections import MultiHostSections
from .abstract import AgentHostSections

if TYPE_CHECKING:
    from .abstract import DataSource, CheckMKAgentDataSource

# TODO: Cluster with different data sources, eg. TCP node and SNMP node:
# - Discovery works.
# - Checking doesn't work - as it was before. Maybe we can handle this in the future.

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
    def __init__(self, hostname, ipaddress):
        # type: (HostName, Optional[HostAddress]) -> None
        super(DataSources, self).__init__()
        self._hostname = hostname
        self._ipaddress = ipaddress

        self._config_cache = config.get_config_cache()
        self._host_config = self._config_cache.get_host_config(hostname)

        self._initialize_data_sources()

        # Has currently no effect. The value possibly set during execution on the single data
        # sources is kept here in this object to return it later on
        self._enforced_check_plugin_names = None  # type: Optional[Set[CheckPluginName]]

    def _initialize_data_sources(self):
        # type: () -> None
        self._sources = {}  # type: Dict[str, DataSource]

        if self._host_config.is_cluster:
            # Cluster hosts do not have any actual data sources
            # Instead all data is provided by the nodes
            return

        self._initialize_agent_based_data_sources()
        self._initialize_snmp_data_sources()
        self._initialize_management_board_data_sources()

    def _initialize_agent_based_data_sources(self):
        # type: () -> None
        if self._host_config.is_all_agents_host:
            source = self._get_agent_data_source(ignore_special_agents=True)
            source.set_main_agent_data_source()
            self._add_source(source)

            self._add_sources(self._get_special_agent_data_sources())

        elif self._host_config.is_all_special_agents_host:
            self._add_sources(self._get_special_agent_data_sources())

        elif self._host_config.is_tcp_host:
            source = self._get_agent_data_source()
            source.set_main_agent_data_source()
            self._add_source(source)

        if "no-piggyback" not in self._host_config.tags:
            self._add_source(PiggyBackDataSource(self._hostname, self._ipaddress))

    def _initialize_snmp_data_sources(self):
        # type: () -> None
        if self._host_config.is_snmp_host:
            self._add_source(SNMPDataSource(self._hostname, self._ipaddress))

    def _initialize_management_board_data_sources(self):
        # type: () -> None
        protocol = self._host_config.management_protocol
        if protocol == "snmp":
            # TODO: Why not hand over management board IP address?
            # TODO: Don't know why pylint does not understand the class hierarchy here. Cleanup the
            # multiple inheritance should solve the issue.
            self._add_source(SNMPManagementBoardDataSource(self._hostname, self._ipaddress))  # pylint: disable=abstract-class-instantiated
        elif protocol == "ipmi":
            # TODO: Why not hand over management board IP address?
            # TODO: Don't know why pylint does not understand the class hierarchy here. Cleanup the
            # multiple inheritance should solve the issue.
            self._add_source(IPMIManagementBoardDataSource(self._hostname, self._ipaddress))  # pylint: disable=abstract-class-instantiated
        elif protocol is None:
            return None
        else:
            raise NotImplementedError()

    def _add_sources(self, sources):
        # type: (Iterable[DataSource]) -> None
        for source in sources:
            self._add_source(source)

    def _add_source(self, source):
        # type: (DataSource) -> None
        self._sources[source.id()] = source

    def describe_data_sources(self):
        # type: () -> str
        if self._host_config.is_all_agents_host:
            return "Normal Checkmk agent, all configured special agents"

        elif self._host_config.is_all_special_agents_host:
            return "No Checkmk agent, all configured special agents"

        elif self._host_config.is_tcp_host:
            return "Normal Checkmk agent, or special agent if configured"

        return "No agent"

    def _get_agent_data_source(self, ignore_special_agents=False):
        # type: (bool) -> CheckMKAgentDataSource
        if not ignore_special_agents:
            special_agents = self._get_special_agent_data_sources()
            if special_agents:
                return special_agents[0]

        datasource_program = self._host_config.datasource_program
        if datasource_program is not None:
            return DSProgramDataSource(self._hostname, self._ipaddress, datasource_program)

        return TCPDataSource(self._hostname, self._ipaddress)

    def _get_special_agent_data_sources(self):
        # type: () -> List[SpecialAgentDataSource]
        return [
            SpecialAgentDataSource(self._hostname, self._ipaddress, agentname, params)
            for agentname, params in self._host_config.special_agents
        ]

    def get_check_plugin_names(self):
        # type: () -> Set[CheckPluginName]
        """Returns the collection of check types the caller may execute on the sections produced
        by these sources.

        Either returns a set of enforced check types (if set before) or ask each individual
        data source for it's supported check types and return a list of these types.
        """
        check_plugin_names = set()

        for source in self._sources.values():
            check_plugin_names.update(source.get_check_plugin_names())

        return check_plugin_names

    def enforce_check_plugin_names(self, check_plugin_names):
        # type: (Set[CheckPluginName]) -> None
        self._enforced_check_plugin_names = check_plugin_names
        for source in self.get_data_sources():
            source.enforce_check_plugin_names(check_plugin_names)

    def get_enforced_check_plugin_names(self):
        # type: () -> Optional[Set[CheckPluginName]]
        """Returns either the collection of enforced check plugin names (when they have been set before) or None"""
        return self._enforced_check_plugin_names

    def get_data_sources(self):
        # type: () -> Iterable[DataSource]
        # Always execute piggyback at the end
        return sorted(self._sources.values(),
                      key=lambda s: (isinstance(s, PiggyBackDataSource), s.id()))

    def set_max_cachefile_age(self, max_cachefile_age):
        # type: (int) -> None
        for source in self.get_data_sources():
            source.set_max_cachefile_age(max_cachefile_age)

    def get_host_sections(self, max_cachefile_age=None):
        # type: (Optional[int]) -> MultiHostSections
        """Gather ALL host info data for any host (hosts, nodes, clusters) in Check_MK.

        Returns a dictionary object of already parsed HostSections() constructs for each related host.
        For single hosts it's just a single entry in the dictionary. For cluster hosts it contains one
        HostSections() entry for each related node.

        Communication errors are not raised through by this functions. All agent related errors are
        caught by the source.run() method and saved in it's _exception attribute. The caller should
        use source.get_summary_result() to get the state, output and perfdata of the agent excecution
        or source.exception() to get the exception object.
        """
        console.step("Fetching data")

        # First abstract clusters/nodes/hosts
        hosts = []
        nodes = self._host_config.nodes
        if nodes is not None:
            for node_hostname in nodes:
                node_ipaddress = ip_lookup.lookup_ip_address(node_hostname)

                node_check_names = check_table.get_needed_check_names(node_hostname,
                                                                      remove_duplicates=True,
                                                                      filter_mode="only_clustered")

                node_data_sources = DataSources(node_hostname, node_ipaddress)
                node_data_sources.enforce_check_plugin_names(node_check_names)
                hosts.append((node_hostname, node_ipaddress, node_data_sources,
                              config.cluster_max_cachefile_age))
        else:
            hosts.append((self._hostname, self._ipaddress, self, config.check_max_cachefile_age))

        if nodes:
            import cmk.base.data_sources.abstract as abstract
            abstract.DataSource.set_may_use_cache_file()

        # Special agents can produce data for the same check_plugin_name on the same host, in this case
        # the section lines need to be extended
        multi_host_sections = MultiHostSections()
        for this_hostname, this_ipaddress, these_sources, this_max_cachefile_age in hosts:
            # In case a max_cachefile_age is given with the function call, always use this one
            # instead of the host individual one. This is only used in discovery mode.
            if max_cachefile_age is not None:
                these_sources.set_max_cachefile_age(max_cachefile_age)
            else:
                these_sources.set_max_cachefile_age(this_max_cachefile_age)

            host_sections =\
                multi_host_sections.add_or_get_host_sections(this_hostname, this_ipaddress,
                        deflt=AgentHostSections())

            for source in these_sources.get_data_sources():
                host_sections_from_source = source.run()
                host_sections.update(host_sections_from_source)

            # Store piggyback information received from all sources of this host. This
            # also implies a removal of piggyback files received during previous calls.
            cmk.utils.piggyback.store_piggyback_raw_data(this_hostname,
                                                         host_sections.piggybacked_raw_data)

        return multi_host_sections
