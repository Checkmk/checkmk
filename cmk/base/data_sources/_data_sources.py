#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# TODO: Cluster with different data sources, eg. TCP node and SNMP node:
# - Discovery works.
# - Checking doesn't work - as it was before. Maybe we can handle this in the future.

import itertools
from typing import Dict, Iterable, Optional, Sequence, Tuple

import cmk.utils.debug
import cmk.utils.paths
import cmk.utils.piggyback
import cmk.utils.tty as tty
from cmk.utils.log import console
from cmk.utils.type_defs import HostAddress, HostName, SourceType

import cmk.base.api.agent_based.register as agent_based_register
import cmk.base.check_table as check_table
import cmk.base.config as config
import cmk.base.ip_lookup as ip_lookup
from cmk.base.config import HostConfig, SelectedRawSections

from ._abstract import ABCConfigurator, ABCChecker, Mode
from .agent import AgentHostSections
from .host_sections import HostKey, MultiHostSections
from .ipmi import IPMIConfigurator
from .piggyback import PiggybackConfigurator
from .programs import DSProgramConfigurator, SpecialAgentConfigurator
from .snmp import SNMPConfigurator
from .tcp import TCPConfigurator

__all__ = ["Checkers", "make_host_sections", "make_configurators", "make_checkers"]

Checkers = Iterable[ABCChecker]


class _Builder:
    """Build a configurator list from host config and raw sections."""
    def __init__(
        self,
        host_config: HostConfig,
        ipaddress: Optional[HostAddress],
        *,
        mode: Mode,
    ) -> None:
        super().__init__()
        self._host_config = host_config
        self._hostname = host_config.hostname
        self._ipaddress = ipaddress
        self._mode = mode
        self._elems: Dict[str, ABCConfigurator] = {}

        self._initialize()

    @property
    def configurators(self) -> Iterable[ABCConfigurator]:
        # Always execute piggyback at the end
        return sorted(
            self._elems.values(),
            key=lambda c: (isinstance(c, PiggybackConfigurator), c.id),
        )

    def _initialize(self) -> None:
        if self._host_config.is_cluster:
            # Cluster hosts do not have any actual data sources
            # Instead all data is provided by the nodes
            return

        self._initialize_agent_based()
        self._initialize_snmp_based()
        self._initialize_mgmt_boards()

    def _initialize_agent_based(self) -> None:
        if self._host_config.is_all_agents_host:
            self._add(self._get_agent(
                ignore_special_agents=True,
                main_data_source=True,
            ))
            for elem in self._get_special_agent():
                self._add(elem)

        elif self._host_config.is_all_special_agents_host:
            for elem in self._get_special_agent():
                self._add(elem)

        elif self._host_config.is_tcp_host:
            self._add(self._get_agent(
                ignore_special_agents=False,
                main_data_source=True,
            ))

        if "no-piggyback" not in self._host_config.tags:
            self._add(PiggybackConfigurator(
                self._hostname,
                self._ipaddress,
                mode=self._mode,
            ))

    def _initialize_snmp_based(self,) -> None:
        if not self._host_config.is_snmp_host:
            return
        self._add(SNMPConfigurator.snmp(
            self._hostname,
            self._ipaddress,
            mode=self._mode,
        ))

    def _initialize_mgmt_boards(self) -> None:
        protocol = self._host_config.management_protocol
        if protocol is None:
            return

        ip_address = ip_lookup.lookup_mgmt_board_ip_address(self._host_config)
        if protocol == "snmp":
            self._add(
                SNMPConfigurator.management_board(
                    self._hostname,
                    ip_address,
                    mode=self._mode,
                ))
        elif protocol == "ipmi":
            self._add(IPMIConfigurator(
                self._hostname,
                ip_address,
                mode=self._mode,
            ))
        else:
            raise LookupError()

    def _add(self, configurator: ABCConfigurator) -> None:
        self._elems[configurator.id] = configurator

    def _get_agent(
        self,
        ignore_special_agents: bool,
        main_data_source: bool,
    ) -> ABCConfigurator:
        if not ignore_special_agents:
            special_agents = self._get_special_agent()
            if special_agents:
                return special_agents[0]

        datasource_program = self._host_config.datasource_program
        if datasource_program is not None:
            return DSProgramConfigurator(
                self._hostname,
                self._ipaddress,
                mode=self._mode,
                main_data_source=main_data_source,
                template=datasource_program,
            )

        return TCPConfigurator(
            self._hostname,
            self._ipaddress,
            mode=self._mode,
            main_data_source=main_data_source,
        )

    def _get_special_agent(self) -> Sequence[ABCConfigurator]:
        return [
            SpecialAgentConfigurator(
                self._hostname,
                self._ipaddress,
                mode=self._mode,
                special_agent_id=agentname,
                params=params,
            ) for agentname, params in self._host_config.special_agents
        ]


def make_configurators(
    host_config: HostConfig,
    ipaddress: Optional[HostAddress],
    *,
    mode: Mode,
) -> Iterable[ABCConfigurator]:
    """Iterable of configurators available for `host_config`."""
    return _Builder(host_config, ipaddress, mode=mode).configurators


def make_checkers(
    host_config: HostConfig,
    ipaddress: Optional[HostAddress],
    *,
    mode: Mode,
) -> Checkers:
    """Iterable of checkers available for `host_config`."""
    return list(c.make_checker() for c in make_configurators(host_config, ipaddress, mode=mode))


def make_host_sections(
    config_cache: config.ConfigCache,
    host_config: HostConfig,
    ipaddress: Optional[HostAddress],
    mode: Mode,
    sources: Checkers,
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
        _make_piggyback_nodes(mode, config_cache, host_config),
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
    return agent_based_register.get_relevant_raw_sections(check_plugin_names=check_plugin_names)


def _make_host_sections(
    nodes: Iterable[Tuple[HostName, Optional[HostAddress], Checkers]],
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
    or source.exception to get the exception object.
    """
    console.verbose("%s+%s %s\n", tty.yellow, tty.normal, "Fetching data".upper())
    # Special agents can produce data for the same check_plugin_name on the same host, in this case
    # the section lines need to be extended
    multi_host_sections = MultiHostSections()
    for hostname, ipaddress, sources in nodes:
        for source in sources:
            source.configurator.file_cache.max_age = max_cachefile_age
            host_sections = multi_host_sections.setdefault(
                HostKey(hostname, ipaddress, source.configurator.source_type),
                source.configurator.default_host_sections,
            )
            # TODO: Select agent / snmp sources before passing
            source.configurator.selected_raw_sections = selected_raw_sections
            with source.configurator.make_fetcher() as fetcher:
                raw_data = fetcher.fetch()
            host_sections.update(source.check(raw_data))

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
        mode: Mode, config_cache: config.ConfigCache,
        host_config: HostConfig) -> Iterable[Tuple[HostName, Optional[HostAddress], Checkers]]:
    """Abstract clusters/nodes/hosts"""
    assert host_config.nodes is not None

    nodes = []
    for hostname in host_config.nodes:
        node_config = config_cache.get_host_config(hostname)
        ipaddress = ip_lookup.lookup_ip_address(node_config)
        sources = make_checkers(
            HostConfig.make_host_config(hostname),
            ipaddress,
            mode=mode,
        )
        nodes.append((hostname, ipaddress, sources))
    return nodes
