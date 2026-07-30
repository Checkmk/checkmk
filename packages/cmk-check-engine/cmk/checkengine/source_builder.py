#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="type-arg"

# TODO: Cluster with different data sources, eg. TCP node and SNMP node:
# - Discovery works.
# - Checking doesn't work - as it was before. Maybe we can handle this in the future.

import socket
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence, Sized
from pathlib import Path
from typing import assert_never, Final, Literal

import cmk.checkengine.sources
from cmk.ccc.hostaddress import HostAddress, HostName
from cmk.checkengine.fetchers.tcp import TLSConfig
from cmk.checkengine.filecache import FileCacheOptions, MaxAge
from cmk.checkengine.helper_interface import FetcherType
from cmk.checkengine.plugins import AgentBasedPlugins
from cmk.checkengine.snmplib import SNMPBackendEnum
from cmk.checkengine.source_abc import OptionalSource, Source, SourceConfig, SourceContext
from cmk.checkengine.sources._sources import (
    IPMISource,
    MgmtSNMPSource,
    MissingIPSource,
    MissingSourceSource,
    PiggybackSource,
    ProgramSource,
    PushAgentSource,
    SNMPSource,
    SpecialAgentSource,
    TCPSource,
)
from cmk.checkengine.subclass_discovery import discover, get_default_identifier
from cmk.ruleset_matcher.tags import ComputedDataSources, TagID
from cmk.server_side_calls_backend import SpecialAgentCommandLine
from cmk.utils.ip_lookup import IPStackConfig


def _discover_optional_sources() -> Mapping[str, type[OptionalSource[Sized]]]:
    return discover(cmk.checkengine.sources, OptionalSource, get_default_identifier)


class SourceBuilder:
    def __init__(
        self,
        plugins: AgentBasedPlugins,
        host_name: HostName,
        host_ip_family: Literal[socket.AddressFamily.AF_INET, socket.AddressFamily.AF_INET6],
        ipaddress: HostAddress | None,
        ip_stack_config: IPStackConfig,
        *,
        simulation_mode: bool,
        source_config: SourceConfig,
        force_snmp_cache_refresh: bool = False,
        snmp_backend: SNMPBackendEnum,
        file_cache_options: FileCacheOptions,
        file_cache_max_age: MaxAge,
        file_cache_path_base: Path,
        file_cache_path_relative: Path,
        tcp_cache_path_relative: Path,
        tls_config: TLSConfig,
        computed_datasources: ComputedDataSources,
        datasource_programs: Sequence[str],
        tag_list: Sequence[TagID],
        management_protocol: Literal["snmp", "ipmi"] | None,
        management_ip: HostAddress | None,
        special_agent_command_lines: Iterable[tuple[str, SpecialAgentCommandLine]],
        is_pull_host: bool,
        check_mk_check_interval: float,
        metrics_association: str | None,
        omd_root: Path,
    ) -> None:
        self.plugins: Final = plugins
        self.host_name: Final = host_name
        self.host_ip_family: Final = host_ip_family
        self._source_config: Final = source_config
        self.ipaddress: Final = ipaddress
        self.ip_stack_config: Final = ip_stack_config
        self.simulation_mode: Final = simulation_mode
        self.max_age_agent: Final = self._max_age_agent(
            simulation_mode, file_cache_options.use_outdated, file_cache_max_age
        )
        self.max_age_snmp: Final = self._max_age_snmp(
            simulation_mode,
            force_snmp_cache_refresh,
            file_cache_options.use_outdated,
            file_cache_max_age,
        )
        self.snmp_backend: Final = snmp_backend
        self.cds: Final = computed_datasources
        self.tag_list: Final = tag_list
        self.management_protocol: Final = management_protocol
        self.management_ip: Final = management_ip
        self.special_agent_command_lines: Final = tuple(special_agent_command_lines)
        self.datasource_programs: Final = datasource_programs
        self.is_pull_host: Final = is_pull_host
        self.check_mk_check_interval: Final = check_mk_check_interval
        self._file_cache_path_base: Final = file_cache_path_base
        self._file_cache_path_relative: Final = file_cache_path_relative
        self._tcp_cache_path_relative: Final = tcp_cache_path_relative
        self.tls_config: Final = tls_config
        self._metrics_association: Final = metrics_association
        self.omd_root: Final = omd_root

        self._elems: dict[str, Source] = {}
        self._initialize_agent_based()
        self._initialize_optional_sources(
            SourceContext(
                host_name=self.host_name,
                ipaddress=self.ipaddress,
                computed_datasources=self.cds,
                max_age_agent=self.max_age_agent,
                file_cache_path_base=self._file_cache_path_base,
                file_cache_path_relative=self._file_cache_path_relative,
                omd_root=self.omd_root,
                metrics_association=self._metrics_association,
                check_mk_check_interval=self.check_mk_check_interval,
            )
        )

        if self.cds.is_tcp and not self._elems:
            # User wants a special agent, a CheckMK agent, or both.  But
            # we didn't configure anything.  Let's report that.
            self._add(MissingSourceSource(self.host_name, self.ipaddress, "API/agent"))

        if TagID("no-piggyback") not in self.tag_list:
            self._add(PiggybackSource(self.host_name, self.ipaddress))

        self._initialize_snmp_based()
        self._initialize_mgmt_boards()

    @staticmethod
    def _max_age_snmp(
        simulation_mode: bool,
        force_snmp_cache_refresh: bool,
        use_outdated: bool,
        max_age: MaxAge,
    ) -> MaxAge:
        if simulation_mode:
            return MaxAge.unlimited()
        if force_snmp_cache_refresh:
            return MaxAge.zero()
        if use_outdated:
            return MaxAge.unlimited()
        return max_age

    @staticmethod
    def _max_age_agent(simulation_mode: bool, use_outdated: bool, max_age: MaxAge) -> MaxAge:
        if simulation_mode:
            return MaxAge.unlimited()
        if use_outdated:
            return MaxAge.unlimited()
        return max_age

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
            totals = Counter(agentname for agentname, _ in self.special_agent_command_lines)
            per_agent_idx: dict[str, int] = {}
            for agentname, agent_data in self.special_agent_command_lines:
                idx = per_agent_idx[agentname] = per_agent_idx.get(agentname, -1) + 1
                yield SpecialAgentSource(
                    self._source_config,
                    self.host_name,
                    self.ipaddress,
                    max_age=self.max_age_agent,
                    agent_name=agentname,
                    cmdline=agent_data.cmdline,
                    stdin=agent_data.stdin,
                    file_cache_path_base=self._file_cache_path_base,
                    file_cache_path_relative=self._file_cache_path_relative,
                    source_idx=None if totals[agentname] == 1 else idx,
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

    def _initialize_optional_sources(self, ctx: SourceContext) -> None:
        # Additive sources that build themselves from the host's source config and are owned by other components.
        for source_cls in _discover_optional_sources().values():
            if (source := source_cls.from_context(ctx)) is not None:
                self._add(source)

    def _initialize_snmp_based(self) -> None:
        if not self.cds.is_snmp:
            return

        if self.simulation_mode or self.snmp_backend is SNMPBackendEnum.STORED_WALK:
            # Here, we bypass NO_IP and silently set the IP to localhost.  This is to accomodate
            # our file-based simulation modes.  However, NO_IP should really be treated as a
            # configuration error with SNMP.  We should try to find a better solution in the future.
            self._add(
                SNMPSource(
                    self._source_config,
                    self.plugins,
                    self.host_name,
                    self.host_ip_family,
                    self.ipaddress or HostAddress("127.0.0.1"),
                    max_age=self.max_age_snmp,
                    file_cache_path_base=self._file_cache_path_base,
                    file_cache_path_relative=self._file_cache_path_relative,
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
                self._source_config,
                self.plugins,
                self.host_name,
                self.host_ip_family,
                self.ipaddress,
                max_age=self.max_age_snmp,
                file_cache_path_base=self._file_cache_path_base,
                file_cache_path_relative=self._file_cache_path_relative,
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
                self._add(
                    MgmtSNMPSource(
                        self._source_config,
                        self.plugins,
                        self.host_name,
                        self.host_ip_family,
                        self.management_ip,
                        max_age=self.max_age_snmp,
                        file_cache_path_base=self._file_cache_path_base,
                        file_cache_path_relative=self._file_cache_path_relative,
                    )
                )
            case "ipmi":
                self._add(
                    IPMISource(
                        self._source_config,
                        self.host_name,
                        self.management_ip,
                        max_age=self.max_age_agent,
                        file_cache_path_base=self._file_cache_path_base,
                        file_cache_path_relative=self._file_cache_path_relative,
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
                    self._source_config,
                    self.host_name,
                    self.host_ip_family,
                    self.ipaddress,
                    program=self.datasource_programs[0],
                    max_age=self.max_age_agent,
                    file_cache_path_base=self._file_cache_path_base,
                    file_cache_path_relative=self._tcp_cache_path_relative,
                )
            )
            return

        if not self.is_pull_host:
            # PUSH
            # add grace period
            interval = int(1.5 * self.check_mk_check_interval)
            self._add(
                source=PushAgentSource(
                    self.host_name,
                    self.ipaddress,
                    max_age=MaxAge(interval, interval, interval),
                    file_cache_path_base=self._file_cache_path_base,
                    file_cache_path_relative=self._file_cache_path_relative,
                )
            )
            return

        # PULL
        if self.ip_stack_config is IPStackConfig.NO_IP:
            return
        if self.ipaddress is None:
            self._add(MissingIPSource(self.host_name, self.ipaddress, "agent"))
            return

        self._add(
            TCPSource(
                self._source_config,
                self.host_name,
                self.host_ip_family,
                self.ipaddress,
                max_age=self.max_age_agent,
                file_cache_path_base=self._file_cache_path_base,
                file_cache_path_relative=self._tcp_cache_path_relative,
                tls_config=self.tls_config,
            )
        )
