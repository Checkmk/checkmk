#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# TODO: Cluster with different data sources, eg. TCP node and SNMP node:
# - Discovery works.
# - Checking doesn't work - as it was before. Maybe we can handle this in the future.

import socket
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import assert_never, Final, Literal

from cmk.ccc.hostaddress import HostAddress, HostName

from cmk.utils.agent_registration import HostAgentConnectionMode
from cmk.utils.ip_lookup import IPStackConfig
from cmk.utils.tags import ComputedDataSources, TagID

from cmk.snmplib import SNMPBackendEnum

from cmk.fetchers import SNMPFetcher, TLSConfig
from cmk.fetchers.filecache import FileCacheOptions, MaxAge

from cmk.checkengine.fetcher import FetcherType
from cmk.checkengine.plugins import AgentBasedPlugins

from cmk.base.snmp_plugin_store import make_plugin_store

from cmk.server_side_calls_backend import SpecialAgentCommandLine

from ._api import Source
from ._sources import (
    FetcherFactory,
    IPMISource,
    MgmtSNMPSource,
    MissingIPSource,
    MissingSourceSource,
    PiggybackSource,
    ProgramSource,
    PushAgentSource,
    SNMPFetcherConfig,
    SNMPSource,
    SpecialAgentSource,
    TCPSource,
)

__all__ = ["make_sources"]


class _Builder:
    def __init__(
        self,
        plugins: AgentBasedPlugins,
        host_name: HostName,
        host_ip_family: Literal[socket.AddressFamily.AF_INET, socket.AddressFamily.AF_INET6],
        ipaddress: HostAddress | None,
        ip_stack_config: IPStackConfig,
        *,
        simulation_mode: bool,
        fetcher_factory: FetcherFactory,
        is_cluster: bool,
        snmp_fetcher_config: SNMPFetcherConfig,
        max_age_agent: MaxAge,
        max_age_snmp: MaxAge,
        snmp_backend: SNMPBackendEnum,
        file_cache_path: Path,
        tcp_cache_path: Path,
        tls_config: TLSConfig,
        computed_datasources: ComputedDataSources,
        datasource_programs: Sequence[str],
        tag_list: Sequence[TagID],
        management_protocol: Literal["snmp", "ipmi"] | None,
        management_ip: HostAddress | None,
        special_agent_command_lines: Iterable[tuple[str, SpecialAgentCommandLine]],
        agent_connection_mode: HostAgentConnectionMode,
        check_mk_check_interval: float,
    ) -> None:
        super().__init__()
        assert not is_cluster

        self.plugins: Final = plugins
        self.host_name: Final = host_name
        self.host_ip_family: Final = host_ip_family
        self.fetcher_factory: Final = fetcher_factory
        self.ipaddress: Final = ipaddress
        self.snmp_fetcher_config: Final = snmp_fetcher_config
        self.ip_stack_config: Final = ip_stack_config
        self.simulation_mode: Final = simulation_mode
        self.max_age_agent: Final = max_age_agent
        self.max_age_snmp: Final = max_age_snmp
        self.snmp_backend: Final = snmp_backend
        self.cds: Final = computed_datasources
        self.tag_list: Final = tag_list
        self.management_protocol: Final = management_protocol
        self.management_ip: Final = management_ip
        self.special_agent_command_lines: Final = special_agent_command_lines
        self.datasource_programs: Final = datasource_programs
        self.agent_connection_mode: Final = agent_connection_mode
        self.check_mk_check_interval: Final = check_mk_check_interval
        self._file_cache_path: Final = file_cache_path
        self._tcp_cache_path: Final = tcp_cache_path
        self.tls_config: Final = tls_config

        self._elems: dict[str, Source] = {}
        self._initialize_agent_based()

        if self.cds.is_tcp and not self._elems:
            # User wants a special agent, a CheckMK agent, or both.  But
            # we didn't configure anything.  Let's report that.
            self._add(MissingSourceSource(self.host_name, self.ipaddress, "API/agent"))

        if TagID("no-piggyback") not in self.tag_list:
            self._add(PiggybackSource(self.fetcher_factory, self.host_name, self.ipaddress))

        self._initialize_snmp_based()
        self._initialize_mgmt_boards()

    @property
    def sources(self) -> Sequence[Source]:
        # Always execute piggyback at the end
        return sorted(
            self._elems.values(),
            key=lambda args: (
                args.source_info().fetcher_type is FetcherType.PIGGYBACK,
                args.source_info().ident,
            ),
        )

    def _initialize_agent_based(self) -> None:
        def make_special_agents() -> Iterable[Source]:
            for agentname, agent_data in self.special_agent_command_lines:
                yield SpecialAgentSource(
                    self.fetcher_factory,
                    self.host_name,
                    self.ipaddress,
                    max_age=self.max_age_agent,
                    agent_name=agentname,
                    cmdline=agent_data.cmdline,
                    stdin=agent_data.stdin,
                    file_cache_path=self._file_cache_path,
                )

        special_agents = tuple(make_special_agents())

        # Translation of the options from WATO (properties of host > monitoring agents)
        #
        #                           all_special_agents  all_agents_host  tcp_host
        # API else CheckMK agent     False               False            True
        # API and Checkmk agent      False               True             True
        # API, no Checkmk agent      True                False            True
        # no API, no Checkmk agent   False               False            False

        if self.cds.is_all_agents_host:
            self._add_agent()
            for elem in special_agents:
                self._add(elem)

        elif self.cds.is_all_special_agents_host:
            for elem in special_agents:
                self._add(elem)

        elif self.cds.is_tcp:
            for elem in special_agents:
                self._add(elem)
            if not special_agents:
                self._add_agent()

    def _initialize_snmp_plugin_store(self) -> None:
        if len(SNMPFetcher.plugin_store) != len(self.plugins.snmp_sections):
            SNMPFetcher.plugin_store = make_plugin_store(self.plugins)

    def _initialize_snmp_based(self) -> None:
        if not self.cds.is_snmp:
            return

        self._initialize_snmp_plugin_store()

        if self.simulation_mode or self.snmp_backend is SNMPBackendEnum.STORED_WALK:
            # Here, we bypass NO_IP and silently set the IP to localhost.  This is to accomodate
            # our file-based simulation modes.  However, NO_IP should really be treated as a
            # configuration error with SNMP.  We should try to find a better solution in the future.
            self._add(
                SNMPSource(
                    self.fetcher_factory,
                    self.plugins,
                    self.host_name,
                    self.host_ip_family,
                    self.ipaddress or HostAddress("127.0.0.1"),
                    fetcher_config=self.snmp_fetcher_config,
                    max_age=self.max_age_snmp,
                    file_cache_path=self._file_cache_path,
                )
            )
            return

        if self.ip_stack_config is IPStackConfig.NO_IP:
            return

        if self.ipaddress is None:
            self._add(MissingIPSource(self.host_name, self.ipaddress, "snmp"))
            return

        self._add(
            SNMPSource(
                self.fetcher_factory,
                self.plugins,
                self.host_name,
                self.host_ip_family,
                self.ipaddress,
                fetcher_config=self.snmp_fetcher_config,
                max_age=self.max_age_snmp,
                file_cache_path=self._file_cache_path,
            )
        )

    def _initialize_mgmt_boards(self) -> None:
        if self.ip_stack_config is IPStackConfig.NO_IP:
            return

        if self.management_protocol is None:
            return

        if self.management_ip is None:
            self._add(MissingIPSource(self.host_name, None, f"mgmt_{self.management_protocol}"))
            return

        match self.management_protocol:
            case "snmp":
                self._initialize_snmp_plugin_store()
                self._add(
                    MgmtSNMPSource(
                        self.fetcher_factory,
                        self.plugins,
                        self.host_name,
                        self.host_ip_family,
                        self.management_ip,
                        fetcher_config=self.snmp_fetcher_config,
                        max_age=self.max_age_snmp,
                        file_cache_path=self._file_cache_path,
                    )
                )
            case "ipmi":
                self._add(
                    IPMISource(
                        self.fetcher_factory,
                        self.host_name,
                        self.management_ip,
                        max_age=self.max_age_agent,
                        file_cache_path=self._file_cache_path,
                    )
                )
            case _:
                assert_never(self.management_protocol)

    def _add(self, source: Source) -> None:
        self._elems[source.source_info().ident] = source

    def _add_agent(self) -> None:
        if self.datasource_programs:
            self._add(
                ProgramSource(
                    self.fetcher_factory,
                    self.host_name,
                    self.host_ip_family,
                    self.ipaddress,
                    program=self.datasource_programs[0],
                    max_age=self.max_age_agent,
                    file_cache_path=self._tcp_cache_path,
                )
            )
            return

        connection_mode = self.agent_connection_mode
        match connection_mode:
            case HostAgentConnectionMode.PUSH:
                # add grace period
                interval = int(1.5 * self.check_mk_check_interval)
                self._add(
                    source=PushAgentSource(
                        self.host_name,
                        self.ipaddress,
                        max_age=MaxAge(interval, interval, interval),
                        file_cache_path=self._file_cache_path,
                    )
                )
            case HostAgentConnectionMode.PULL:
                if self.ip_stack_config is IPStackConfig.NO_IP:
                    return
                if self.ipaddress is None:
                    self._add(MissingIPSource(self.host_name, self.ipaddress, "agent"))
                    return
                self._add(
                    TCPSource(
                        self.fetcher_factory,
                        self.host_name,
                        self.host_ip_family,
                        self.ipaddress,
                        max_age=self.max_age_agent,
                        file_cache_path=self._tcp_cache_path,
                        tls_config=self.tls_config,
                    )
                )
            case _:
                assert_never(connection_mode)


def make_sources(
    plugins: AgentBasedPlugins,
    host_name: HostName,
    host_ip_family: Literal[socket.AddressFamily.AF_INET, socket.AddressFamily.AF_INET6],
    ipaddress: HostAddress | None,
    ip_stack_config: IPStackConfig,
    *,
    fetcher_factory: FetcherFactory,
    is_cluster: bool,
    force_snmp_cache_refresh: bool = False,
    snmp_fetcher_config: SNMPFetcherConfig,
    snmp_backend: SNMPBackendEnum,
    simulation_mode: bool,
    file_cache_options: FileCacheOptions,
    file_cache_max_age: MaxAge,
    file_cache_path: Path,
    tcp_cache_path: Path,
    tls_config: TLSConfig,
    computed_datasources: ComputedDataSources,
    datasource_programs: Sequence[str],
    tag_list: Sequence[TagID],
    management_ip: HostAddress | None,
    management_protocol: Literal["snmp", "ipmi"] | None,
    special_agent_command_lines: Iterable[tuple[str, SpecialAgentCommandLine]],
    agent_connection_mode: HostAgentConnectionMode,
    check_mk_check_interval: float,
) -> Sequence[Source]:
    """Sequence of sources available for `host_config`."""
    if is_cluster:
        # Cluster hosts do not have any actual data sources
        # Instead all data is provided by the nodes
        return ()

    def max_age_snmp() -> MaxAge:
        if simulation_mode:
            return MaxAge.unlimited()
        if force_snmp_cache_refresh:
            return MaxAge.zero()
        if file_cache_options.use_outdated:
            return MaxAge.unlimited()
        return file_cache_max_age

    def max_age_agent() -> MaxAge:
        if simulation_mode:
            return MaxAge.unlimited()
        if file_cache_options.use_outdated:
            return MaxAge.unlimited()
        return file_cache_max_age

    return _Builder(
        plugins,
        host_name,
        host_ip_family,
        ipaddress,
        ip_stack_config,
        simulation_mode=simulation_mode,
        fetcher_factory=fetcher_factory,
        snmp_fetcher_config=snmp_fetcher_config,
        snmp_backend=snmp_backend,
        is_cluster=is_cluster,
        max_age_agent=max_age_agent(),
        max_age_snmp=max_age_snmp(),
        file_cache_path=file_cache_path,
        tcp_cache_path=tcp_cache_path,
        tls_config=tls_config,
        computed_datasources=computed_datasources,
        datasource_programs=datasource_programs,
        tag_list=tag_list,
        management_ip=management_ip,
        management_protocol=management_protocol,
        special_agent_command_lines=special_agent_command_lines,
        agent_connection_mode=agent_connection_mode,
        check_mk_check_interval=check_mk_check_interval,
    ).sources
