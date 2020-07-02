#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# TODO: Cluster with different data sources, eg. TCP node and SNMP node:
# - Discovery works.
# - Checking doesn't work - as it was before. Maybe we can handle this in the future.

import collections.abc
from typing import Dict, Iterable, List, Optional

from cmk.utils.check_utils import maincheckify
import cmk.utils.debug
import cmk.utils.paths
import cmk.utils.piggyback
import cmk.utils.tty as tty
from cmk.utils.log import console
from cmk.utils.type_defs import CheckPluginName, HostAddress, HostName, SourceType

import cmk.base.check_table as check_table
import cmk.base.config as config
import cmk.base.ip_lookup as ip_lookup
from cmk.base.config import HostConfig, SelectedRawSections

from ._utils import management_board_ipaddress
from .abstract import DataSource
from .agent import AgentDataSource, AgentHostSections
from .host_sections import MultiHostSections
from .ipmi import IPMIManagementBoardDataSource
from .piggyback import PiggyBackDataSource
from .programs import DSProgramDataSource, SpecialAgentDataSource
from .snmp import SNMPDataSource, SNMPManagementBoardDataSource
from .tcp import TCPDataSource

__all__ = ["DataSources"]


class SourceBuilder:
    """Build the source list from host config and raw sections."""
    def __init__(self, host_config: HostConfig, ipaddress: Optional[HostAddress],
                 selected_raw_sections: Optional[SelectedRawSections]) -> None:
        super(SourceBuilder, self).__init__()
        self._host_config = host_config
        self._hostname = host_config.hostname
        self._ipaddress = ipaddress
        self._sources: Dict[str, DataSource] = {}

        self._initialize_data_sources(selected_raw_sections)

    @property
    def sources(self) -> List[DataSource]:
        # Always execute piggyback at the end
        return sorted(self._sources.values(),
                      key=lambda s: (isinstance(s, PiggyBackDataSource), s.id()))

    def _initialize_data_sources(self,
                                 selected_raw_sections: Optional[SelectedRawSections]) -> None:
        if self._host_config.is_cluster:
            # Cluster hosts do not have any actual data sources
            # Instead all data is provided by the nodes
            return

        self._initialize_agent_based_data_sources(selected_raw_sections)
        self._initialize_snmp_data_sources(selected_raw_sections)
        self._initialize_management_board_data_sources(selected_raw_sections)

    def _initialize_agent_based_data_sources(
            self, selected_raw_sections: Optional[SelectedRawSections]) -> None:
        if self._host_config.is_all_agents_host:
            self._add_source(
                self._get_agent_data_source(
                    ignore_special_agents=True,
                    selected_raw_sections=selected_raw_sections,
                    main_data_source=True,
                ))
            self._add_sources(
                self._get_special_agent_data_sources(selected_raw_sections=selected_raw_sections,))

        elif self._host_config.is_all_special_agents_host:
            self._add_sources(
                self._get_special_agent_data_sources(selected_raw_sections=selected_raw_sections,))

        elif self._host_config.is_tcp_host:
            self._add_source(
                self._get_agent_data_source(
                    ignore_special_agents=False,
                    selected_raw_sections=selected_raw_sections,
                    main_data_source=True,
                ))

        if "no-piggyback" not in self._host_config.tags:
            self._add_source(
                PiggyBackDataSource(
                    self._hostname,
                    self._ipaddress,
                    selected_raw_sections=selected_raw_sections,
                ))

    def _initialize_snmp_data_sources(self,
                                      selected_raw_sections: Optional[SelectedRawSections]) -> None:
        if not self._host_config.is_snmp_host:
            return
        self._add_source(
            SNMPDataSource(
                self._hostname,
                self._ipaddress,
                selected_raw_sections=selected_raw_sections,
            ))

    def _initialize_management_board_data_sources(
            self, selected_raw_sections: Optional[SelectedRawSections]) -> None:
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

    def _add_sources(self, sources: Iterable[DataSource]) -> None:
        for source in sources:
            self._add_source(source)

    def _add_source(self, source: DataSource) -> None:
        self._sources[source.id()] = source

    def _get_agent_data_source(
        self,
        ignore_special_agents: bool,
        selected_raw_sections: Optional[SelectedRawSections],
        main_data_source: bool,
    ) -> AgentDataSource:
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
                main_data_source=main_data_source,
            )

        return TCPDataSource(
            self._hostname,
            self._ipaddress,
            selected_raw_sections=selected_raw_sections,
            main_data_source=main_data_source,
        )

    def _get_special_agent_data_sources(
        self,
        selected_raw_sections: Optional[SelectedRawSections],
    ) -> List[SpecialAgentDataSource]:
        return [
            SpecialAgentDataSource(
                self._hostname,
                self._ipaddress,
                agentname,
                params,
                selected_raw_sections=selected_raw_sections,
            ) for agentname, params in self._host_config.special_agents
        ]


def make_sources(host_config: HostConfig, ipaddress: Optional[HostAddress],
                 selected_raw_sections: Optional[SelectedRawSections]) -> List[DataSource]:
    return SourceBuilder(host_config, ipaddress, selected_raw_sections).sources


def make_description(host_config: HostConfig) -> str:
    if host_config.is_all_agents_host:
        return "Normal Checkmk agent, all configured special agents"

    if host_config.is_all_special_agents_host:
        return "No Checkmk agent, all configured special agents"

    if host_config.is_tcp_host:
        return "Normal Checkmk agent, or special agent if configured"

    return "No agent"


class DataSources(collections.abc.Collection):
    def __init__(
        self,
        host_config: HostConfig,
        ipaddress: Optional[HostAddress],
        # optional set: None -> no selection, empty -> select *nothing*
        selected_raw_sections: Optional[SelectedRawSections] = None,
    ) -> None:
        super(DataSources, self).__init__()
        self._ipaddress = ipaddress
        self._host_config = host_config
        self._sources = make_sources(host_config, ipaddress, selected_raw_sections)
        self.description = make_description(host_config)

    @property
    def _hostname(self) -> HostName:
        return self._host_config.hostname

    def __contains__(self, item) -> bool:
        return self._sources.__contains__(item)

    def __iter__(self):
        return self._sources.__iter__()

    def __len__(self):
        return self._sources.__len__()

    def get_host_sections(self, max_cachefile_age: Optional[int] = None) -> MultiHostSections:
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

        if max_cachefile_age is None:
            # In case a max_cachefile_age is given with the function call, always use this one
            # instead of the host individual one. This is only used in discovery mode.
            max_cachefile_age = (config.check_max_cachefile_age if self._host_config.nodes is None
                                 else config.cluster_max_cachefile_age)

        # First abstract clusters/nodes/hosts
        if self._host_config.nodes is not None:
            nodes = []
            for hostname in self._host_config.nodes:
                ipaddress = ip_lookup.lookup_ip_address(hostname)

                check_names = check_table.get_needed_check_names(
                    hostname,
                    remove_duplicates=True,
                    filter_mode="only_clustered",
                )
                node_needed_raw_sections = config.get_relevant_raw_sections(
                    # TODO (mo): centralize maincheckify: CMK-4295
                    CheckPluginName(maincheckify(n)) for n in check_names)

                sources = DataSources(
                    self._host_config,
                    ipaddress,
                    node_needed_raw_sections,
                )
                nodes.append((hostname, ipaddress, sources))
        else:
            nodes = [(self._hostname, self._ipaddress, self)]

        if self._host_config.nodes:
            import cmk.base.data_sources.abstract as abstract  # pylint: disable=import-outside-toplevel
            abstract.DataSource.set_may_use_cache_file()

        # Special agents can produce data for the same check_plugin_name on the same host, in this case
        # the section lines need to be extended
        multi_host_sections = MultiHostSections()
        for hostname, ipaddress, sources in nodes:
            for source in sources:
                source.set_max_cachefile_age(max_cachefile_age)
                host_sections = AgentHostSections()
                host_sections.update(source.run())
                multi_host_sections.set_default_host_sections(
                    (hostname, ipaddress, source.source_type),
                    host_sections,
                )

            # Store piggyback information received from all sources of this host. This
            # also implies a removal of piggyback files received during previous calls.
            host_sections = AgentHostSections()
            multi_host_sections.set_default_host_sections(
                (hostname, ipaddress, SourceType.HOST),
                host_sections,
            )
            cmk.utils.piggyback.store_piggyback_raw_data(
                hostname,
                host_sections.piggybacked_raw_data,
            )

        return multi_host_sections
