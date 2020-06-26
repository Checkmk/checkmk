#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Naming:
#
# raw data:      The raw unparsed data produced by the data source (_execute()).
#                For the agent this is the whole byte string received from the
#                agent. For SNMP this is a python data structure containing
#                all OID/values received from SNMP.
# host_sections: A wrapper object for the "sections" and other information like
#                cache info and piggyback lines that is used to process the
#                data within Check_MK.

from typing import Iterable, TYPE_CHECKING, List, Dict, Optional, Set

import cmk.utils.paths
import cmk.utils.debug
import cmk.utils.piggyback
import cmk.utils.tty as tty
from cmk.utils.type_defs import HostAddress, HostName, PluginName, SectionName, SourceType
from cmk.utils.log import console

from cmk.base.api.agent_based.section_types import AgentSectionPlugin, SNMPSectionPlugin
from cmk.base.api.agent_based.register.check_plugins_legacy import maincheckify
import cmk.base.config as config
from cmk.base.config import HostConfig, SectionPlugin
import cmk.base.ip_lookup as ip_lookup
import cmk.base.check_table as check_table
from cmk.base.check_utils import CheckPluginNameStr

from .snmp import SNMPDataSource, SNMPManagementBoardDataSource
from .ipmi import IPMIManagementBoardDataSource
from .tcp import TCPDataSource
from .piggyback import PiggyBackDataSource
from .programs import DSProgramDataSource, SpecialAgentDataSource
from .host_sections import MultiHostSections
from .abstract import AgentHostSections, management_board_ipaddress

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


class DataSources:
    def __init__(
            self,
            host_config,  # type: HostConfig
            hostname,  # type: HostName
            ipaddress,  # type: Optional[HostAddress]
            # optional set: None -> no selection, empty -> select *nothing*
        selected_raw_sections=None,  # type: Optional[Dict[SectionName, SectionPlugin]]
    ):
        # type: (...) -> None
        super(DataSources, self).__init__()
        self._hostname = hostname
        self._ipaddress = ipaddress
        assert host_config.hostname == hostname
        self._host_config = host_config
        self._sources = {}  # type: Dict[str, DataSource]

        self._initialize_data_sources(selected_raw_sections)

    def _initialize_data_sources(self, selected_raw_sections):
        # type: (Optional[Dict[SectionName, SectionPlugin]]) -> None
        if self._host_config.is_cluster:
            # Cluster hosts do not have any actual data sources
            # Instead all data is provided by the nodes
            return

        self._initialize_agent_based_data_sources(selected_raw_sections)
        self._initialize_snmp_data_sources(selected_raw_sections)
        self._initialize_management_board_data_sources(selected_raw_sections)

    def _initialize_agent_based_data_sources(self, selected_raw_sections):
        # type: (Optional[Dict[SectionName, SectionPlugin]]) -> None
        if self._host_config.is_all_agents_host:
            source = self._get_agent_data_source(
                ignore_special_agents=True,
                selected_raw_sections=selected_raw_sections,
            )
            source.set_main_agent_data_source()
            self._add_source(source)

            self._add_sources(
                self._get_special_agent_data_sources(selected_raw_sections=selected_raw_sections,))

        elif self._host_config.is_all_special_agents_host:
            self._add_sources(
                self._get_special_agent_data_sources(selected_raw_sections=selected_raw_sections,))

        elif self._host_config.is_tcp_host:
            source = self._get_agent_data_source(
                ignore_special_agents=False,
                selected_raw_sections=selected_raw_sections,
            )
            source.set_main_agent_data_source()
            self._add_source(source)

        if "no-piggyback" not in self._host_config.tags:
            piggy_source = PiggyBackDataSource(
                self._hostname,
                self._ipaddress,
                selected_raw_sections=selected_raw_sections,
            )
            self._add_source(piggy_source)

    def _initialize_snmp_data_sources(self, selected_raw_sections):
        # type: (Optional[Dict[SectionName, SectionPlugin]]) -> None
        if not self._host_config.is_snmp_host:
            return
        snmp_source = SNMPDataSource(
            self._hostname,
            self._ipaddress,
            selected_raw_sections=selected_raw_sections,
        )
        self._add_source(snmp_source)

    def _initialize_management_board_data_sources(self, selected_raw_sections):
        # type: (Optional[Dict[SectionName, SectionPlugin]]) -> None
        protocol = self._host_config.management_protocol
        if protocol is None:
            return

        ip_address = management_board_ipaddress(self._hostname)
        if protocol == "snmp":
            self._add_source(
                SNMPManagementBoardDataSource(
                    self._hostname,
                    ip_address,
                    selected_raw_sections=selected_raw_sections,
                ))
        elif protocol == "ipmi":
            self._add_source(
                IPMIManagementBoardDataSource(
                    self._hostname,
                    ip_address,
                    selected_raw_sections=selected_raw_sections,
                ))
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

        if self._host_config.is_all_special_agents_host:
            return "No Checkmk agent, all configured special agents"

        if self._host_config.is_tcp_host:
            return "Normal Checkmk agent, or special agent if configured"

        return "No agent"

    def _get_agent_data_source(
            self,
            ignore_special_agents,  # type: bool
            selected_raw_sections,  # type: Optional[Dict[SectionName, SectionPlugin]]
    ):
        # type: (...) -> CheckMKAgentDataSource
        if not ignore_special_agents:
            special_agents = self._get_special_agent_data_sources(
                selected_raw_sections=selected_raw_sections,)
            if special_agents:
                return special_agents[0]

        datasource_program = self._host_config.datasource_program
        if datasource_program is not None:
            return DSProgramDataSource(
                self._hostname,
                self._ipaddress,
                datasource_program,
                selected_raw_sections=selected_raw_sections,
            )

        return TCPDataSource(
            self._hostname,
            self._ipaddress,
            selected_raw_sections=selected_raw_sections,
        )

    def _get_special_agent_data_sources(
            self,
            selected_raw_sections,  # type: Optional[Dict[SectionName, SectionPlugin]]
    ):
        # type: (...) -> List[SpecialAgentDataSource]
        return [
            SpecialAgentDataSource(
                self._hostname,
                self._ipaddress,
                agentname,
                params,
                selected_raw_sections=selected_raw_sections,
            ) for agentname, params in self._host_config.special_agents
        ]

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
        console.verbose("%s+%s %s\n", tty.yellow, tty.normal, "Fetching data".upper())

        # First abstract clusters/nodes/hosts
        hosts = []
        nodes = self._host_config.nodes
        if nodes is not None:
            for node_hostname in nodes:
                node_ipaddress = ip_lookup.lookup_ip_address(node_hostname)

                node_check_names = check_table.get_needed_check_names(node_hostname,
                                                                      remove_duplicates=True,
                                                                      filter_mode="only_clustered")
                node_needed_raw_sections = config.get_relevant_raw_sections(
                    # TODO (mo): centralize maincheckify: CMK-4295
                    PluginName(maincheckify(n)) for n in node_check_names)

                node_data_sources = DataSources(
                    self._host_config,
                    node_hostname,
                    node_ipaddress,
                    node_needed_raw_sections,
                )
                hosts.append((node_hostname, node_ipaddress, node_data_sources,
                              config.cluster_max_cachefile_age))
        else:
            hosts.append((self._hostname, self._ipaddress, self, config.check_max_cachefile_age))

        if nodes:
            import cmk.base.data_sources.abstract as abstract  # pylint: disable=import-outside-toplevel
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

            for source in these_sources.get_data_sources():
                host_sections_from_source = source.run()
                multi_host_sections.setdefault_host_sections(
                    (this_hostname, this_ipaddress, source.source_type),
                    AgentHostSections(),
                ).update(host_sections_from_source)

            # Store piggyback information received from all sources of this host. This
            # also implies a removal of piggyback files received during previous calls.
            host_sections = multi_host_sections.setdefault_host_sections(
                (this_hostname, this_ipaddress, SourceType.HOST),
                AgentHostSections(),
            )
            cmk.utils.piggyback.store_piggyback_raw_data(this_hostname,
                                                         host_sections.piggybacked_raw_data)

        return multi_host_sections
