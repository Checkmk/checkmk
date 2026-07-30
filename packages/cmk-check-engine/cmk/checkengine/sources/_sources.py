#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"
# mypy: disable-error-code="explicit-override"
# mypy: disable-error-code="type-arg"

import os.path
import socket
from pathlib import Path
from typing import Final, Literal

from cmk.ccc.hostaddress import HostAddress, HostName
from cmk.checkengine.fetcher_abc import Fetcher
from cmk.checkengine.fetchers.ipmi import IPMIFetcher
from cmk.checkengine.fetchers.nofetcher import NoFetcher, NoFetcherError
from cmk.checkengine.fetchers.piggyback import PiggybackFetcher
from cmk.checkengine.fetchers.program import ProgramFetcher
from cmk.checkengine.fetchers.snmp import SNMPFetcher, SNMPScanConfig
from cmk.checkengine.fetchers.tcp import TCPFetcher, TLSConfig
from cmk.checkengine.filecache import (
    AgentFileCache,
    FileCache,
    FileCacheMode,
    FileCacheOptions,
    MaxAge,
    NoCache,
    SNMPFileCache,
)
from cmk.checkengine.helper_interface import AgentRawData, FetcherType, SourceInfo, SourceType
from cmk.checkengine.plugins import AgentBasedPlugins
from cmk.checkengine.snmplib import SNMPRawData
from cmk.checkengine.source_abc import Source, SourceConfig

__all__ = [
    "SNMPSource",
    "MgmtSNMPSource",
    "IPMISource",
    "ProgramSource",
    "PushAgentSource",
    "TCPSource",
    "SpecialAgentSource",
    "PiggybackSource",
    "MissingIPSource",
    "MissingSourceSource",
]

# Singleton
_NO_CACHE: Final[FileCache] = NoCache()


def _make_snmp_fetcher(
    source_config: SourceConfig,
    plugins: AgentBasedPlugins,
    host_name: HostName,
    host_ip_family: Literal[socket.AddressFamily.AF_INET, socket.AddressFamily.AF_INET6],
    ip_address: HostAddress,
    source_type: SourceType,
) -> SNMPFetcher:
    """Assemble the SNMP fetcher from the configuration data.

    Shared by the host and management-board SNMP sources, which differ only in
    their ``source_type``.
    """
    snmp_fetcher_config = source_config.snmp_fetcher_config
    return SNMPFetcher(
        sections=source_config.snmp_sections(plugins, host_name),
        plugin_store=source_config.snmp_plugin_store(plugins),
        scan_config=SNMPScanConfig(
            on_error=snmp_fetcher_config.on_error,
            missing_sys_description=snmp_fetcher_config.missing_sys_description(host_name),
        ),
        do_status_data_inventory=source_config.snmp_status_data_inventory(host_name),
        base_path=snmp_fetcher_config.base_path,
        relative_section_cache_path=snmp_fetcher_config.relative_section_cache_path,
        snmp_config=source_config.snmp_config(host_name, host_ip_family, ip_address, source_type),
        caching_config=snmp_fetcher_config.caching_config(host_name),
        relative_stored_walk_path=snmp_fetcher_config.relative_stored_walk_path,
        relative_walk_cache_path=snmp_fetcher_config.relative_walk_cache_path,
        force_stored_walks=snmp_fetcher_config.force_stored_walks,
    )


class SNMPSource(Source[SNMPRawData]):
    fetcher_type: Final = FetcherType.SNMP
    source_type: Final = SourceType.HOST

    def __init__(
        self,
        source_config: SourceConfig,
        plugins: AgentBasedPlugins,
        host_name: HostName,
        host_ip_family: Literal[socket.AddressFamily.AF_INET, socket.AddressFamily.AF_INET6],
        ipaddress: HostAddress,
        *,
        max_age: MaxAge,
        file_cache_path_base: Path,
        file_cache_path_relative: Path,
    ) -> None:
        super().__init__()
        self._source_config: Final = source_config
        self._plugins: Final = plugins
        self.host_name: Final = host_name
        self.host_ip_family: Final = host_ip_family
        self.ipaddress: Final = ipaddress
        self._max_age: Final = max_age
        self._file_cache_path_base: Final = file_cache_path_base
        self._file_cache_path_relative: Final = file_cache_path_relative

    def source_info(self) -> SourceInfo:
        return SourceInfo(
            self.host_name,
            self.ipaddress,
            "snmp",
            self.fetcher_type,
            self.source_type,
        )

    def fetcher(self) -> Fetcher:
        return _make_snmp_fetcher(
            self._source_config,
            self._plugins,
            self.host_name,
            self.host_ip_family,
            self.ipaddress,
            self.source_type,
        )

    def file_cache(
        self, *, simulation: bool, file_cache_options: FileCacheOptions
    ) -> FileCache[SNMPRawData]:
        return SNMPFileCache(
            base_path=self._file_cache_path_base,
            relative_path_template=os.path.join(
                self._file_cache_path_relative,
                self.source_info().ident,
                "{mode}",
                str(self.host_name),
            ),
            max_age=self._max_age,
            simulation=simulation,
            use_only_cache=file_cache_options.use_only_cache,
            file_cache_mode=file_cache_options.file_cache_mode(),
        )


class MgmtSNMPSource(Source[SNMPRawData]):
    fetcher_type: Final = FetcherType.SNMP
    source_type: Final = SourceType.MANAGEMENT

    def __init__(
        self,
        source_config: SourceConfig,
        plugins: AgentBasedPlugins,
        host_name: HostName,
        host_ip_family: Literal[socket.AddressFamily.AF_INET, socket.AddressFamily.AF_INET6],
        ipaddress: HostAddress,
        *,
        max_age: MaxAge,
        file_cache_path_base: Path,
        file_cache_path_relative: Path,
    ) -> None:
        super().__init__()
        self._source_config: Final = source_config
        self._plugins: Final = plugins
        self.host_name: Final = host_name
        self.host_ip_family: Final = host_ip_family
        self.ipaddress: Final = ipaddress
        self._max_age: Final = max_age
        self._file_cache_path_base: Final = file_cache_path_base
        self._file_cache_path_relative: Final = file_cache_path_relative

    def source_info(self) -> SourceInfo:
        return SourceInfo(
            self.host_name,
            self.ipaddress,
            "mgmt_snmp",
            self.fetcher_type,
            self.source_type,
        )

    def fetcher(self) -> Fetcher:
        return _make_snmp_fetcher(
            self._source_config,
            self._plugins,
            self.host_name,
            self.host_ip_family,
            self.ipaddress,
            self.source_type,
        )

    def file_cache(
        self, *, simulation: bool, file_cache_options: FileCacheOptions
    ) -> FileCache[SNMPRawData]:
        return SNMPFileCache(
            base_path=self._file_cache_path_base,
            relative_path_template=os.path.join(
                self._file_cache_path_relative,
                self.source_info().ident,
                "{mode}",
                str(self.host_name),
            ),
            max_age=self._max_age,
            simulation=simulation,
            use_only_cache=file_cache_options.use_only_cache,
            file_cache_mode=file_cache_options.file_cache_mode(),
        )


class IPMISource(Source[AgentRawData]):
    fetcher_type: Final = FetcherType.IPMI
    source_type: Final = SourceType.MANAGEMENT

    def __init__(
        self,
        source_config: SourceConfig,
        host_name: HostName,
        ipaddress: HostAddress,
        *,
        max_age: MaxAge,
        file_cache_path_base: Path,
        file_cache_path_relative: Path,
    ) -> None:
        super().__init__()
        self._source_config: Final = source_config
        self.host_name: Final = host_name
        self.ipaddress: Final = ipaddress
        self._max_age: Final = max_age
        self._file_cache_path_base: Final = file_cache_path_base
        self._file_cache_path_relative: Final = file_cache_path_relative

    def source_info(self) -> SourceInfo:
        return SourceInfo(
            self.host_name,
            self.ipaddress,
            "mgmt_ipmi",
            self.fetcher_type,
            self.source_type,
        )

    def fetcher(self) -> IPMIFetcher:
        username, password = self._source_config.ipmi_credentials(self.host_name)
        return IPMIFetcher(
            address=self.ipaddress,
            username=username,
            password=password,
        )

    def file_cache(
        self, *, simulation: bool, file_cache_options: FileCacheOptions
    ) -> FileCache[AgentRawData]:
        return AgentFileCache(
            base_path=self._file_cache_path_base,
            relative_path_template=os.path.join(
                self._file_cache_path_relative, self.source_info().ident, str(self.host_name)
            ),
            max_age=self._max_age,
            simulation=simulation,
            use_only_cache=file_cache_options.use_only_cache,
            file_cache_mode=file_cache_options.file_cache_mode(),
        )


class ProgramSource(Source[AgentRawData]):
    fetcher_type: Final = FetcherType.PROGRAM
    source_type: Final = SourceType.HOST

    def __init__(
        self,
        source_config: SourceConfig,
        host_name: HostName,
        host_ip_family: Literal[socket.AddressFamily.AF_INET, socket.AddressFamily.AF_INET6],
        ipaddress: HostAddress | None,
        *,
        program: str,
        max_age: MaxAge,
        file_cache_path_base: Path,
        file_cache_path_relative: Path,
    ) -> None:
        super().__init__()
        self._source_config: Final = source_config
        self.host_name: Final = host_name
        self.host_ip_family: Final = host_ip_family
        self.ipaddress: Final = ipaddress
        self.program: Final = program
        self._max_age: Final = max_age
        self._file_cache_path_base: Final = file_cache_path_base
        self._file_cache_path_relative: Final = file_cache_path_relative

    def source_info(self) -> SourceInfo:
        return SourceInfo(
            self.host_name,
            self.ipaddress,
            "agent",  # collides with TCPSource, not sure if intentional.
            self.fetcher_type,
            self.source_type,
        )

    def fetcher(self) -> ProgramFetcher:
        return ProgramFetcher(
            cmdline=self._source_config.program_commandline(
                self.host_name, self.host_ip_family, self.ipaddress, self.program
            ),
            stdin=None,
            is_cmc=self._source_config.is_cmc,
        )

    def file_cache(
        self, *, simulation: bool, file_cache_options: FileCacheOptions
    ) -> FileCache[AgentRawData]:
        return AgentFileCache(
            base_path=self._file_cache_path_base,
            relative_path_template=os.path.join(self._file_cache_path_relative, self.host_name),
            max_age=self._max_age,
            simulation=simulation,
            use_only_cache=file_cache_options.use_only_cache,
            file_cache_mode=file_cache_options.file_cache_mode(),
        )


class PushAgentSource(Source[AgentRawData]):
    fetcher_type: Final = FetcherType.PUSH_AGENT
    source_type: Final = SourceType.HOST

    def __init__(
        self,
        host_name: HostName,
        ipaddress: HostAddress | None,
        *,
        max_age: MaxAge,
        file_cache_path_base: Path,
        file_cache_path_relative: Path,
    ) -> None:
        super().__init__()
        self.host_name: Final = host_name
        self.ipaddress: Final = ipaddress
        self._max_age: Final = max_age
        self._file_cache_path_base: Final = file_cache_path_base
        self._file_cache_path_relative: Final = file_cache_path_relative

    def source_info(self) -> SourceInfo:
        return SourceInfo(
            self.host_name,
            self.ipaddress,
            "push-agent",
            self.fetcher_type,
            self.source_type,
        )

    def fetcher(self) -> NoFetcher:
        return NoFetcher(NoFetcherError.NO_FETCHER)

    def file_cache(
        self, *, simulation: bool, file_cache_options: FileCacheOptions
    ) -> FileCache[AgentRawData]:
        return AgentFileCache(
            base_path=self._file_cache_path_base,
            relative_path_template=os.path.join(
                self._file_cache_path_relative,
                self.source_info().ident,
                str(self.host_name),
                "agent_output",
            ),
            max_age=(
                MaxAge.unlimited()
                if simulation or file_cache_options.use_outdated
                else self._max_age
            ),
            simulation=simulation,
            use_only_cache=True,
            # Push agents have no live fetcher (NoFetcher), so the cache is the only data source.
            # Disabling the cache would mean no data at all, which breaks CLI discovery (-I/-II).
            file_cache_mode=FileCacheMode.READ,
        )


class TCPSource(Source[AgentRawData]):
    fetcher_type: Final = FetcherType.TCP
    source_type: Final = SourceType.HOST

    def __init__(
        self,
        source_config: SourceConfig,
        host_name: HostName,
        host_ip_family: Literal[socket.AddressFamily.AF_INET, socket.AddressFamily.AF_INET6],
        ipaddress: HostAddress,
        *,
        max_age: MaxAge,
        file_cache_path_base: Path,
        file_cache_path_relative: Path,
        tls_config: TLSConfig,
    ) -> None:
        super().__init__()
        self._source_config: Final = source_config
        self.host_name: Final = host_name
        self.host_ip_family: Final = host_ip_family
        self.ipaddress: Final = ipaddress
        self._max_age: Final = max_age
        self._file_cache_path_base: Final = file_cache_path_base
        self._file_cache_path_relative: Final = file_cache_path_relative
        self._tls_config: Final = tls_config

    def source_info(self) -> SourceInfo:
        return SourceInfo(
            self.host_name,
            self.ipaddress,
            "agent",
            self.fetcher_type,
            self.source_type,
        )

    def fetcher(self) -> TCPFetcher:
        tcp_fetcher_config = self._source_config.tcp_fetcher_config
        return TCPFetcher(
            host_name=self.host_name,
            address=(self.ipaddress, tcp_fetcher_config.agent_port(self.host_name)),
            family=self.host_ip_family,
            timeout=tcp_fetcher_config.connect_timeout(self.host_name),
            encryption_handling=tcp_fetcher_config.parsed_encryption_handling(self.host_name),
            uuid_file=self._source_config.uuid_lookup_dir / self.host_name,
            pre_shared_secret=tcp_fetcher_config.symmetric_agent_encryption(self.host_name),
            tls_config=self._tls_config,
        )

    def file_cache(
        self, *, simulation: bool, file_cache_options: FileCacheOptions
    ) -> FileCache[AgentRawData]:
        return AgentFileCache(
            base_path=self._file_cache_path_base,
            relative_path_template=os.path.join(self._file_cache_path_relative, self.host_name),
            max_age=self._max_age,
            simulation=simulation,
            use_only_cache=(
                file_cache_options.tcp_use_only_cache or file_cache_options.use_only_cache
            ),
            file_cache_mode=file_cache_options.file_cache_mode(),
        )


class SpecialAgentSource(Source[AgentRawData]):
    fetcher_type: Final = FetcherType.SPECIAL_AGENT
    source_type: Final = SourceType.HOST

    def __init__(
        self,
        source_config: SourceConfig,
        host_name: HostName,
        ipaddress: HostAddress | None,
        *,
        max_age: MaxAge,
        agent_name: str,
        stdin: str | None,
        cmdline: str,
        file_cache_path_base: Path,
        file_cache_path_relative: Path,
        source_idx: int | None = None,
    ) -> None:
        super().__init__()
        self._source_config: Final = source_config
        self.host_name: Final = host_name
        self.ipaddress: Final = ipaddress
        self._max_age: Final = max_age
        self._agent_name: Final = agent_name
        self._stdin: Final = stdin
        self._cmdline: Final = cmdline
        self._file_cache_path_base: Final = file_cache_path_base
        self._file_cache_path_relative: Final = file_cache_path_relative
        self._source_idx: Final = source_idx

    def source_info(self) -> SourceInfo:
        ident = f"special_{self._agent_name}"
        if self._source_idx is not None:
            ident = f"{ident}_{self._source_idx}"
        return SourceInfo(
            self.host_name,
            self.ipaddress,
            ident,
            self.fetcher_type,
            self.source_type,
        )

    def fetcher(self) -> ProgramFetcher:
        return ProgramFetcher(
            cmdline=self._cmdline,
            stdin=self._stdin,
            is_cmc=self._source_config.is_cmc,
        )

    def file_cache(
        self, *, simulation: bool, file_cache_options: FileCacheOptions
    ) -> FileCache[AgentRawData]:
        return AgentFileCache(
            base_path=self._file_cache_path_base,
            relative_path_template=os.path.join(
                self._file_cache_path_relative, self.source_info().ident, str(self.host_name)
            ),
            max_age=self._max_age,
            simulation=simulation,
            use_only_cache=file_cache_options.use_only_cache,
            file_cache_mode=file_cache_options.file_cache_mode(),
        )


class PiggybackSource(Source[AgentRawData]):
    fetcher_type: Final = FetcherType.PIGGYBACK
    source_type: Final = SourceType.HOST

    def __init__(
        self,
        host_name: HostName,
        ipaddress: HostAddress | None,
    ) -> None:
        super().__init__()
        self.host_name: Final = host_name
        self.ipaddress: Final = ipaddress

    def source_info(self) -> SourceInfo:
        return SourceInfo(
            self.host_name,
            self.ipaddress,
            "piggyback",
            self.fetcher_type,
            self.source_type,
        )

    def fetcher(self) -> PiggybackFetcher:
        return PiggybackFetcher()

    def file_cache(
        self,
        *,
        simulation: bool,  # noqa: ARG002
        file_cache_options: FileCacheOptions,  # noqa: ARG002
    ) -> FileCache[AgentRawData]:
        return _NO_CACHE


class MissingIPSource(Source):
    fetcher_type: Final = FetcherType.NONE
    source_type: Final = SourceType.HOST

    def __init__(self, host_name: HostName, ipaddress: None, ident: str) -> None:
        super().__init__()
        self.host_name: Final = host_name
        self.ipaddress: Final = ipaddress
        self.ident: Final = ident

    def source_info(self) -> SourceInfo:
        return SourceInfo(
            self.host_name,
            self.ipaddress,
            self.ident,
            self.fetcher_type,
            self.source_type,
        )

    def fetcher(self) -> NoFetcher:
        return NoFetcher(NoFetcherError.MISSING_IP)

    def file_cache(self, *, simulation: bool, file_cache_options: FileCacheOptions) -> FileCache:  # noqa: ARG002
        return _NO_CACHE


class MissingSourceSource(Source):
    fetcher_type: Final = FetcherType.NONE
    source_type: Final = SourceType.HOST

    def __init__(self, host_name: HostName, ipaddress: HostAddress | None, ident: str) -> None:
        super().__init__()
        self.host_name: Final = host_name
        self.ipaddress: Final = ipaddress
        self.ident: Final = ident

    def source_info(self) -> SourceInfo:
        return SourceInfo(
            self.host_name,
            self.ipaddress,
            self.ident,
            self.fetcher_type,
            self.source_type,
        )

    def fetcher(self) -> NoFetcher:
        return NoFetcher(NoFetcherError.NO_FETCHER)

    def file_cache(self, *, simulation: bool, file_cache_options: FileCacheOptions) -> FileCache:  # noqa: ARG002
        return _NO_CACHE
