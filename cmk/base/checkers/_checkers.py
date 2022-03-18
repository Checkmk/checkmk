#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# TODO: Cluster with different data sources, eg. TCP node and SNMP node:
# - Discovery works.
# - Checking doesn't work - as it was before. Maybe we can handle this in the future.

from typing import Dict, Iterable, Iterator, List, Optional, Sequence, Tuple

import cmk.utils.debug
import cmk.utils.paths
import cmk.utils.piggyback
import cmk.utils.tty as tty
from cmk.utils.cpu_tracking import CPUTracker
from cmk.utils.log import console
from cmk.utils.type_defs import HostAddress, HostName, result, SourceType

from cmk.fetchers import MaxAge
from cmk.fetchers.protocol import FetcherMessage

import cmk.base.config as config
import cmk.base.core_config as core_config
import cmk.base.ip_lookup as ip_lookup
from cmk.base.config import HostConfig

from ._abstract import Mode, Source
from .agent import AgentHostSections
from .host_sections import HostKey, HostSections, MultiHostSections
from .ipmi import IPMISource
from .piggyback import PiggybackSource
from .programs import DSProgramSource, SpecialAgentSource
from .snmp import SNMPSource
from .tcp import TCPSource
from .type_defs import NO_SELECTION, SectionNameCollection

__all__ = ["fetch_all", "update_host_sections", "make_sources", "make_nodes"]


class _Builder:
    """Build a source list from host config and raw sections."""
    def __init__(
        self,
        host_config: HostConfig,
        ipaddress: Optional[HostAddress],
        *,
        mode: Mode,
        selected_sections: SectionNameCollection,
    ) -> None:
        super().__init__()
        self._host_config = host_config
        self._hostname = host_config.hostname
        self._ipaddress = ipaddress
        self._fallback_ip = core_config.fallback_ip_for(
            self._host_config,
            6 if self._host_config.is_ipv6_primary else 4,
        )
        self._mode = mode
        self._selected_sections = selected_sections
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

    def _initialize_snmp_based(self) -> None:
        if not self._host_config.is_snmp_host:
            return
        self._add(
            SNMPSource.snmp(
                self._hostname,
                self._ipaddress,
                mode=self._mode,
                selected_sections=self._selected_sections,
            ))

    def _initialize_mgmt_boards(self) -> None:
        protocol = self._host_config.management_protocol
        if protocol is None:
            return

        ip_address = ip_lookup.lookup_mgmt_board_ip_address(self._host_config)
        if ip_address is None:
            # HostAddress is not Optional.
            #
            # See above.
            return
        if protocol == "snmp":
            self._add(
                SNMPSource.management_board(
                    self._hostname,
                    ip_address,
                    mode=self._mode,
                    selected_sections=self._selected_sections,
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
                self._ipaddress or self._fallback_ip,
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
                self._ipaddress or self._fallback_ip,
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
    selected_sections: SectionNameCollection = NO_SELECTION,
) -> Sequence[Source]:
    """Sequence of sources available for `host_config`."""
    return _Builder(
        host_config,
        ipaddress,
        mode=mode,
        selected_sections=selected_sections,
    ).sources


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


def fetch_all(
    nodes: Iterable[Tuple[HostName, Optional[HostAddress], Sequence[Source]]],
    *,
    max_cachefile_age: MaxAge,
    host_config: HostConfig,
) -> Iterator[FetcherMessage]:
    console.verbose("%s+%s %s\n", tty.yellow, tty.normal, "Fetching data".upper())
    # TODO(ml): It is not clear to me in which case it is possible for the following to hold true
    #           for any source in nodes:
    #             - hostname != source.hostname
    #             - ipaddress != source.ipaddress
    #           If this is impossible, then we do not need the Tuple[HostName, HostAddress, ...].
    for _hostname, _ipaddress, sources in nodes:
        for source in sources:
            console.vverbose("  Source: %s/%s\n" % (source.source_type, source.fetcher_type))

            source.file_cache_max_age = max_cachefile_age

            with CPUTracker() as tracker:
                raw_data = source.fetch()
            yield FetcherMessage.from_raw_data(
                raw_data,
                tracker.duration,
                source.fetcher_type,
            )


def update_host_sections(
    multi_host_sections: MultiHostSections,
    nodes: Iterable[Tuple[HostName, Optional[HostAddress], Sequence[Source]]],
    *,
    max_cachefile_age: MaxAge,
    host_config: HostConfig,
    fetcher_messages: Sequence[FetcherMessage],
    selected_sections: SectionNameCollection,
) -> Sequence[Tuple[Source, result.Result[HostSections, Exception]]]:
    """Gather ALL host info data for any host (hosts, nodes, clusters) in Check_MK.

    Communication errors are not raised through by this functions. All agent related errors are
    caught by the source.run() method and saved in it's _exception attribute. The caller should
    use source.get_summary_result() to get the state, output and perfdata of the agent excecution
    or source.exception to get the exception object.
    """
    console.verbose("%s+%s %s\n", tty.yellow, tty.normal, "Parse fetcher results".upper())

    flat_node_sources = [(hn, ip, src) for hn, ip, sources in nodes for src in sources]

    # TODO (ml): Can we somehow verify that this is correct?
    #if fetcher_message["fetcher_type"] != source.id:
    #    raise LookupError("Checker and fetcher missmatch")
    # (mo): this is not enough, but better than nothing:
    if len(flat_node_sources) != len(fetcher_messages):
        raise LookupError("Checker and fetcher missmatch")

    # Special agents can produce data for the same check_plugin_name on the same host, in this case
    # the section lines need to be extended
    data: List[Tuple[Source, result.Result[HostSections, Exception]]] = []
    for fetcher_message, (hostname, ipaddress, source) in zip(fetcher_messages, flat_node_sources):
        console.vverbose("  Source: %s/%s\n" % (source.source_type, source.fetcher_type))

        source.file_cache_max_age = max_cachefile_age

        host_sections = multi_host_sections.setdefault(
            HostKey(hostname, ipaddress, source.source_type),
            source.default_host_sections,
        )

        source_result = source.parse(fetcher_message.raw_data, selection=selected_sections)
        data.append((source, source_result))
        if source_result.is_ok():
            console.vverbose("  -> Add sections: %s\n" %
                             sorted([str(s) for s in source_result.ok.sections.keys()]))
            host_sections.add(source_result.ok)
        else:
            console.vverbose("  -> Not adding sections: %s\n" % source_result.error)

    for hostname, ipaddress, _sources in nodes:
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
