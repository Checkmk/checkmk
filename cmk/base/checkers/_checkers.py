#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# TODO: Cluster with different data sources, eg. TCP node and SNMP node:
# - Discovery works.
# - Checking doesn't work - as it was before. Maybe we can handle this in the future.

import itertools
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import cmk.utils.debug
import cmk.utils.paths
import cmk.utils.piggyback
import cmk.utils.tty as tty
from cmk.utils.log import console
from cmk.utils.type_defs import HostAddress, HostName, result, SourceType

from cmk.fetchers.controller import FetcherMessage

import cmk.base.api.agent_based.register as agent_based_register
import cmk.base.check_table as check_table
import cmk.base.config as config
import cmk.base.ip_lookup as ip_lookup
from cmk.base.config import HostConfig, SelectedRawSections

from ._abstract import Source, Mode, HostSections
from .agent import AgentHostSections
from .host_sections import HostKey, MultiHostSections
from .ipmi import IPMISource
from .piggyback import PiggybackSource
from .programs import DSProgramSource, SpecialAgentSource
from .snmp import SNMPSource
from .tcp import TCPSource

__all__ = ["update_host_sections", "make_sources", "make_nodes"]


class _Builder:
    """Build a source list from host config and raw sections."""
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
        self._elems: Dict[str, Source] = {}

        self._initialize()

    @property
    def sources(self) -> Sequence[Source]:
        # Always execute piggyback at the end
        return sorted(
            self._elems.values(),
            key=lambda c: (isinstance(c, PiggybackSource), c.id),
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
            for elem in self._get_special_agents():
                self._add(elem)

        elif self._host_config.is_all_special_agents_host:
            for elem in self._get_special_agents():
                self._add(elem)

        elif self._host_config.is_tcp_host:
            self._add(self._get_agent(
                ignore_special_agents=False,
                main_data_source=True,
            ))

        if "no-piggyback" not in self._host_config.tags:
            self._add(PiggybackSource(
                self._hostname,
                self._ipaddress,
                mode=self._mode,
            ))

    def _initialize_snmp_based(self,) -> None:
        if not self._host_config.is_snmp_host:
            return
        assert self._ipaddress is not None
        self._add(SNMPSource.snmp(
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
            self._add(SNMPSource.management_board(
                self._hostname,
                ip_address,
                mode=self._mode,
            ))
        elif protocol == "ipmi":
            self._add(IPMISource(
                self._hostname,
                ip_address,
                mode=self._mode,
            ))
        else:
            raise LookupError()

    def _add(self, source: Source) -> None:
        self._elems[source.id] = source

    def _get_agent(
        self,
        ignore_special_agents: bool,
        main_data_source: bool,
    ) -> Source:
        if not ignore_special_agents:
            special_agents = self._get_special_agents()
            if special_agents:
                return special_agents[0]

        datasource_program = self._host_config.datasource_program
        if datasource_program is not None:
            return DSProgramSource(
                self._hostname,
                self._ipaddress,
                mode=self._mode,
                main_data_source=main_data_source,
                template=datasource_program,
            )

        return TCPSource(
            self._hostname,
            self._ipaddress,
            mode=self._mode,
            main_data_source=main_data_source,
        )

    def _get_special_agents(self) -> Sequence[Source]:
        return [
            SpecialAgentSource(
                self._hostname,
                self._ipaddress,
                mode=self._mode,
                special_agent_id=agentname,
                params=params,
            ) for agentname, params in self._host_config.special_agents
        ]


def make_sources(
    host_config: HostConfig,
    ipaddress: Optional[HostAddress],
    *,
    mode: Mode,
) -> Sequence[Source]:
    """Sequence of sources available for `host_config`."""
    return _Builder(host_config, ipaddress, mode=mode).sources


def make_nodes(
    config_cache: config.ConfigCache,
    host_config: HostConfig,
    ipaddress: Optional[HostAddress],
    mode: Mode,
    sources: Sequence[Source],
) -> Sequence[Tuple[HostName, Optional[HostAddress], Sequence[Source]]]:
    if host_config.nodes is None:
        return [(host_config.hostname, ipaddress, sources)]
    return _make_piggyback_nodes(mode, config_cache, host_config)


def _make_piggybacked_sections(host_config) -> SelectedRawSections:
    check_plugin_names = set(
        itertools.chain.from_iterable(
            check_table.get_needed_check_names(
                node_name,
                filter_mode="only_clustered",
            ) for node_name in host_config.nodes))
    return agent_based_register.get_relevant_raw_sections(
        check_plugin_names=check_plugin_names,
        # TODO: this was added when an optional argument became
        # mandatory. So this makes the default explicit, but
        # currently I am not sure if this is correct.
        consider_inventory_plugins=False,
    )


def update_host_sections(
    multi_host_sections: MultiHostSections,
    nodes: Iterable[Tuple[HostName, Optional[HostAddress], Sequence[Source]]],
    *,
    max_cachefile_age: int,
    selected_raw_sections: Optional[SelectedRawSections],
    host_config: HostConfig,
    fetcher_messages: Optional[Sequence[FetcherMessage]] = None,
) -> Sequence[Tuple[Source, result.Result[HostSections, Exception]]]:
    """Gather ALL host info data for any host (hosts, nodes, clusters) in Check_MK.

    Communication errors are not raised through by this functions. All agent related errors are
    caught by the source.run() method and saved in it's _exception attribute. The caller should
    use source.get_summary_result() to get the state, output and perfdata of the agent excecution
    or source.exception to get the exception object.
    """
    if fetcher_messages is None:
        console.verbose("%s+%s %s\n", tty.yellow, tty.normal, "Fetching data".upper())
    else:
        console.verbose("%s+%s %s\n", tty.yellow, tty.normal, "Parse fetcher results".upper())

    # Special agents can produce data for the same check_plugin_name on the same host, in this case
    # the section lines need to be extended
    data: List[Tuple[Source, result.Result[HostSections, Exception]]] = []
    for hostname, ipaddress, sources in nodes:
        for source_index, source in enumerate(sources):
            console.vverbose("  Source: %s/%s\n" % (source.source_type, source.fetcher_type))
            if host_config.nodes is None:
                source.selected_raw_sections = selected_raw_sections
            else:
                source.selected_raw_sections = _make_piggybacked_sections(host_config)

            source.file_cache_max_age = max_cachefile_age

            host_sections = multi_host_sections.setdefault(
                HostKey(hostname, ipaddress, source.source_type),
                source.default_host_sections,
            )

            if fetcher_messages is None:
                # We don't have raw_data yet (from the previously executed fetcher), execute the
                # fetcher here.
                raw_data = source.fetch()
            else:
                # The Microcore has handed over results from the previously executed fetcher.
                # Extract the raw_data for the source we currently
                fetcher_message = fetcher_messages[source_index]
                # TODO (ml): Can we somehow verify that this is correct?
                #if fetcher_message["fetcher_type"] != source.id:
                #    raise LookupError("Checker and fetcher missmatch")
                raw_data = fetcher_message.raw_data

            source_result = source.parse(raw_data)
            data.append((source, source_result))
            if source_result.is_ok():
                console.vverbose("  -> Add sections: %s\n" %
                                 sorted([str(s) for s in source_result.ok.sections.keys()]))
                host_sections.update(source_result.ok)
            else:
                console.vverbose("  -> Not adding sections: %s\n" % source_result.error)

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

    return data


def _make_piggyback_nodes(
    mode: Mode,
    config_cache: config.ConfigCache,
    host_config: HostConfig,
) -> Sequence[Tuple[HostName, Optional[HostAddress], Sequence[Source]]]:
    """Abstract clusters/nodes/hosts"""
    assert host_config.nodes is not None

    nodes = []
    for hostname in host_config.nodes:
        node_config = config_cache.get_host_config(hostname)
        ipaddress = ip_lookup.lookup_ip_address(node_config)
        sources = make_sources(
            HostConfig.make_host_config(hostname),
            ipaddress,
            mode=mode,
        )
        nodes.append((hostname, ipaddress, sources))
    return nodes
