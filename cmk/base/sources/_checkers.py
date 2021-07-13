#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# TODO: Cluster with different data sources, eg. TCP node and SNMP node:
# - Discovery works.
# - Checking doesn't work - as it was before. Maybe we can handle this in the future.

from typing import Dict, Final, Iterable, Iterator, Optional, Sequence, Tuple

import cmk.utils.tty as tty
from cmk.utils.cpu_tracking import CPUTracker
from cmk.utils.exceptions import OnError
from cmk.utils.log import console
from cmk.utils.type_defs import HostAddress, HostName

import cmk.core_helpers.cache as file_cache
from cmk.core_helpers.protocol import FetcherMessage
from cmk.core_helpers.type_defs import NO_SELECTION, SectionNameCollection

import cmk.base.config as config
import cmk.base.ip_lookup as ip_lookup
from cmk.base.config import HostConfig

from ._abstract import Mode, Source
from .push_agent import PushAgentSource
from .ipmi import IPMISource
from .piggyback import PiggybackSource
from .programs import DSProgramSource, SpecialAgentSource
from .snmp import SNMPSource
from .tcp import TCPSource

__all__ = ["fetch_all", "make_sources", "make_nodes"]


class _Builder:
    """Build a source list from host config and raw sections."""
    def __init__(
        self,
        host_config: HostConfig,
        ipaddress: Optional[HostAddress],
        *,
        selected_sections: SectionNameCollection,
        on_scan_error: OnError,
        force_snmp_cache_refresh: bool,
    ) -> None:
        super().__init__()
        self.host_config: Final = host_config
        self.ipaddress: Final = ipaddress
        self.selected_sections: Final = selected_sections
        self.on_scan_error: Final = on_scan_error
        self.force_snmp_cache_refresh: Final = force_snmp_cache_refresh
        self._fallback_ip: Final = ip_lookup.fallback_ip_for(
            self.host_config.default_address_family)
        self._elems: Dict[str, Source] = {}

        self._initialize()

    @property
    def hostname(self) -> HostName:
        return self.host_config.hostname

    @property
    def sources(self) -> Sequence[Source]:
        # Always execute piggyback at the end
        return sorted(
            self._elems.values(),
            key=lambda c: (isinstance(c, PiggybackSource), c.id),
        )

    def _initialize(self) -> None:
        if self.host_config.is_cluster:
            # Cluster hosts do not have any actual data sources
            # Instead all data is provided by the nodes
            return

        self._initialize_agent_based()
        self._initialize_snmp_based()
        self._initialize_mgmt_boards()

    def _initialize_agent_based(self) -> None:
        if self.host_config.is_all_agents_host:
            self._add(self._get_agent(
                ignore_special_agents=True,
                main_data_source=True,
            ))
            for elem in self._get_special_agents():
                self._add(elem)

        elif self.host_config.is_all_special_agents_host:
            for elem in self._get_special_agents():
                self._add(elem)

        elif self.host_config.is_tcp_host:
            self._add(self._get_agent(
                ignore_special_agents=False,
                main_data_source=True,
            ))

        if "no-piggyback" not in self.host_config.tags:
            self._add(PiggybackSource(self.hostname, self.ipaddress))

    def _initialize_snmp_based(self) -> None:
        if not self.host_config.is_snmp_host:
            return
        if self.ipaddress is None:
            # HostAddress is not Optional.
            #
            # At least classic SNMP enforces that there is an address set,
            # Inline-SNMP has some lookup logic for some reason. We need
            # to find out whether or not we can really have None here.
            # Looks like it could be the case for cluster hosts which
            # don't have an IP address set.
            return
        self._add(
            SNMPSource.snmp(
                self.hostname,
                self.ipaddress,
                selected_sections=self.selected_sections,
                on_scan_error=self.on_scan_error,
                force_cache_refresh=self.force_snmp_cache_refresh,
            ))

    def _initialize_mgmt_boards(self) -> None:
        protocol = self.host_config.management_protocol
        if protocol is None:
            return

        ip_address = config.lookup_mgmt_board_ip_address(self.host_config)
        if ip_address is None:
            # HostAddress is not Optional.
            #
            # See above.
            return
        if protocol == "snmp":
            self._add(
                SNMPSource.management_board(
                    self.hostname,
                    ip_address,
                    selected_sections=self.selected_sections,
                    on_scan_error=self.on_scan_error,
                    force_cache_refresh=self.force_snmp_cache_refresh,
                ))
        elif protocol == "ipmi":
            self._add(IPMISource(
                self.hostname,
                ip_address,
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

        datasource_program = self.host_config.datasource_program
        if datasource_program is not None:
            return DSProgramSource(
                self.hostname,
                self.ipaddress or self._fallback_ip,
                main_data_source=main_data_source,
                template=datasource_program,
            )

        connection_mode = self.host_config.agent_connection_mode()
        if connection_mode == "push-agent":
            return PushAgentSource(self.hostname)
        if connection_mode == "pull-agent":
            return TCPSource(
                self.hostname,
                self.ipaddress,
                main_data_source=main_data_source,
            )
        raise NotImplementedError(f"connection mode {connection_mode!r}")

    def _get_special_agents(self) -> Sequence[Source]:
        return [
            SpecialAgentSource(
                self.hostname,
                self.ipaddress or self._fallback_ip,
                special_agent_id=agentname,
                params=params,
            ) for agentname, params in self.host_config.special_agents
        ]


def make_sources(
    host_config: HostConfig,
    ipaddress: Optional[HostAddress],
    *,
    force_snmp_cache_refresh: bool = False,
    selected_sections: SectionNameCollection = NO_SELECTION,
    on_scan_error: OnError = OnError.RAISE,
) -> Sequence[Source]:
    """Sequence of sources available for `host_config`."""
    return _Builder(
        host_config,
        ipaddress,
        selected_sections=selected_sections,
        on_scan_error=on_scan_error,
        force_snmp_cache_refresh=force_snmp_cache_refresh,
    ).sources


def make_nodes(
    config_cache: config.ConfigCache,
    host_config: HostConfig,
    ipaddress: Optional[HostAddress],
    sources: Sequence[Source],
) -> Sequence[Tuple[HostName, Optional[HostAddress], Sequence[Source]]]:
    if host_config.nodes is None:
        return [(host_config.hostname, ipaddress, sources)]
    return _make_cluster_nodes(config_cache, host_config)


def fetch_all(
    *,
    nodes: Iterable[Tuple[HostName, Optional[HostAddress], Sequence[Source]]],
    file_cache_max_age: file_cache.MaxAge,
    mode: Mode,
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

            source.file_cache_max_age = file_cache_max_age

            with CPUTracker() as tracker:
                raw_data = source.fetch(mode)
            yield FetcherMessage.from_raw_data(
                raw_data,
                tracker.duration,
                source.fetcher_type,
            )


def _make_cluster_nodes(
    config_cache: config.ConfigCache,
    host_config: HostConfig,
) -> Sequence[Tuple[HostName, Optional[HostAddress], Sequence[Source]]]:
    """Abstract clusters/nodes/hosts"""
    assert host_config.nodes is not None

    nodes = []
    for hostname in host_config.nodes:
        node_config = config_cache.get_host_config(hostname)
        ipaddress = config.lookup_ip_address(node_config)
        sources = make_sources(
            HostConfig.make_host_config(hostname),
            ipaddress,
            force_snmp_cache_refresh=False,
        )
        nodes.append((hostname, ipaddress, sources))
    return nodes
