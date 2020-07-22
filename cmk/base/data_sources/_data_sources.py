#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# TODO: Cluster with different data sources, eg. TCP node and SNMP node:
# - Discovery works.
# - Checking doesn't work - as it was before. Maybe we can handle this in the future.

import itertools
from typing import Dict, Iterable, List, Optional, Tuple

import cmk.utils.debug
import cmk.utils.paths
import cmk.utils.piggyback
import cmk.utils.tty as tty
from cmk.utils.log import console
from cmk.utils.type_defs import HostAddress, HostName, SourceType

import cmk.base.check_table as check_table
import cmk.base.config as config
import cmk.base.ip_lookup as ip_lookup
from cmk.base.config import HostConfig, SelectedRawSections

from ._abstract import ABCDataSource
from .agent import AgentDataSource, AgentHostSections
from .host_sections import HostKey, MultiHostSections
from .ipmi import IPMIConfigurator, IPMIManagementBoardDataSource
from .piggyback import PiggyBackConfigurator, PiggyBackDataSource
from .programs import (
    DSProgramConfigurator,
    SpecialAgentConfigurator,
    ProgramDataSource,
)
from .snmp import SNMPConfigurator, SNMPDataSource
from .tcp import TCPConfigurator, TCPDataSource

__all__ = ["DataSources", "make_host_sections", "make_sources"]

DataSources = Iterable[ABCDataSource]


class SourceBuilder:
    """Build the source list from host config and raw sections."""
    def __init__(
        self,
        host_config: HostConfig,
        ipaddress: Optional[HostAddress],
    ) -> None:
        super(SourceBuilder, self).__init__()
        self._host_config = host_config
        self._hostname = host_config.hostname
        self._ipaddress = ipaddress
        self._sources: Dict[str, ABCDataSource] = {}

        self._initialize_data_sources()

    @property
    def sources(self) -> DataSources:
        # Always execute piggyback at the end
        return sorted(self._sources.values(),
                      key=lambda s: (isinstance(s, PiggyBackDataSource), s.configurator.id))

    def _initialize_data_sources(self) -> None:
        if self._host_config.is_cluster:
            # Cluster hosts do not have any actual data sources
            # Instead all data is provided by the nodes
            return

        self._initialize_agent_based_data_sources()
        self._initialize_snmp_data_sources()
        self._initialize_management_board_data_sources()

    def _initialize_agent_based_data_sources(self) -> None:
        if self._host_config.is_all_agents_host:
            self._add_source(
                self._get_agent_data_source(
                    ignore_special_agents=True,
                    main_data_source=True,
                ))
            self._add_sources(self._get_special_agent_data_sources())

        elif self._host_config.is_all_special_agents_host:
            self._add_sources(self._get_special_agent_data_sources())

        elif self._host_config.is_tcp_host:
            self._add_source(
                self._get_agent_data_source(
                    ignore_special_agents=False,
                    main_data_source=True,
                ))

        if "no-piggyback" not in self._host_config.tags:
            self._add_source(
                PiggyBackDataSource(configurator=PiggyBackConfigurator(
                    self._hostname,
                    self._ipaddress,
                ),))

    def _initialize_snmp_data_sources(self,) -> None:
        if not self._host_config.is_snmp_host:
            return
        self._add_source(
            SNMPDataSource(configurator=SNMPConfigurator.snmp(
                self._hostname,
                self._ipaddress,
            ),))

    def _initialize_management_board_data_sources(self) -> None:
        protocol = self._host_config.management_protocol
        if protocol is None:
            return

        ip_address = ip_lookup.lookup_mgmt_board_ip_address(self._host_config)
        if protocol == "snmp":
            self._add_source(
                SNMPDataSource(configurator=SNMPConfigurator.management_board(
                    self._hostname,
                    ip_address,
                ),))
        elif protocol == "ipmi":
            self._add_source(
                IPMIManagementBoardDataSource(configurator=IPMIConfigurator(
                    self._hostname, ip_address),))
        else:
            raise NotImplementedError()

    def _add_sources(self, sources: DataSources) -> None:
        for source in sources:
            self._add_source(source)

    def _add_source(self, source: ABCDataSource) -> None:
        self._sources[source.configurator.id] = source

    def _get_agent_data_source(
        self,
        ignore_special_agents: bool,
        main_data_source: bool,
    ) -> AgentDataSource:
        if not ignore_special_agents:
            special_agents = self._get_special_agent_data_sources()
            if special_agents:
                return special_agents[0]

        datasource_program = self._host_config.datasource_program
        if datasource_program is not None:
            return ProgramDataSource(
                configurator=DSProgramConfigurator(
                    self._hostname,
                    self._ipaddress,
                    template=datasource_program,
                ),
                main_data_source=main_data_source,
            )

        return TCPDataSource(
            configurator=TCPConfigurator(self._hostname, self._ipaddress),
            main_data_source=main_data_source,
        )

    def _get_special_agent_data_sources(self) -> List[ProgramDataSource]:
        return [
            ProgramDataSource(configurator=SpecialAgentConfigurator(
                self._hostname,
                self._ipaddress,
                special_agent_id=agentname,
                params=params,
            ),) for agentname, params in self._host_config.special_agents
        ]


def make_sources(
    host_config: HostConfig,
    ipaddress: Optional[HostAddress],
) -> DataSources:
    """Return a list of sources for DataSources.

    Args:
        host_config: The host configuration.
        ipaddress: The host address.

    """
    return SourceBuilder(host_config, ipaddress).sources


def make_host_sections(
    config_cache: config.ConfigCache,
    host_config: HostConfig,
    ipaddress: Optional[HostAddress],
    sources: DataSources,
    *,
    max_cachefile_age: int,
    selected_raw_sections: Optional[SelectedRawSections],
) -> MultiHostSections:
    if host_config.nodes is None:
        return _make_host_sections(
            [(host_config.hostname, ipaddress, sources)],
            max_cachefile_age=max_cachefile_age,
            selected_raw_sections=selected_raw_sections,
        )

    return _make_host_sections(
        _make_piggyback_nodes(config_cache, host_config),
        max_cachefile_age=max_cachefile_age,
        selected_raw_sections=_make_piggybacked_sections(host_config),
    )


def _make_piggybacked_sections(host_config) -> SelectedRawSections:
    check_plugin_names = set(
        itertools.chain.from_iterable(
            check_table.get_needed_check_names(
                node_name,
                remove_duplicates=True,
                filter_mode="only_clustered",
            ) for node_name in host_config.nodes))
    return config.get_relevant_raw_sections(check_plugin_names=check_plugin_names)


def _make_host_sections(
    nodes: Iterable[Tuple[HostName, Optional[HostAddress], DataSources]],
    *,
    max_cachefile_age: int,
    selected_raw_sections: Optional[SelectedRawSections],
) -> MultiHostSections:
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
    # Special agents can produce data for the same check_plugin_name on the same host, in this case
    # the section lines need to be extended
    multi_host_sections = MultiHostSections()
    for hostname, ipaddress, sources in nodes:
        for source in sources:
            source.set_max_cachefile_age(max_cachefile_age)
            host_sections = multi_host_sections.setdefault(
                HostKey(hostname, ipaddress, source.configurator.source_type),
                source._empty_host_sections(),
            )
            host_sections.update(
                # TODO: Select agent / snmp sources before passing
                source.run(selected_raw_sections=selected_raw_sections))

        # Store piggyback information received from all sources of this host. This
        # also implies a removal of piggyback files received during previous calls.
        host_sections = multi_host_sections.setdefault(
            HostKey(hostname, ipaddress, SourceType.HOST),
            AgentHostSections(),
        )
        cmk.utils.piggyback.store_piggyback_raw_data(
            hostname,
            host_sections.piggybacked_raw_data,
        )

    return multi_host_sections


def _make_piggyback_nodes(
        config_cache: config.ConfigCache,
        host_config: HostConfig) -> Iterable[Tuple[HostName, Optional[HostAddress], DataSources]]:
    """Abstract clusters/nodes/hosts"""
    assert host_config.nodes is not None

    nodes = []
    for hostname in host_config.nodes:
        node_config = config_cache.get_host_config(hostname)
        ipaddress = ip_lookup.lookup_ip_address(node_config)
        sources = make_sources(
            HostConfig.make_host_config(hostname),
            ipaddress,
        )
        nodes.append((hostname, ipaddress, sources))
    return nodes
