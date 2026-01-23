#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="type-arg"

# TODO This module should be freed from base deps.

import os.path
import socket
from pathlib import Path
from typing import Final, Literal, Protocol

from cmk.ccc.hostaddress import HostAddress, HostName
from cmk.checkengine.plugins import AgentBasedPlugins
from cmk.fetchers import (
    Fetcher,
    IPMIFetcher,
    NoFetcher,
    NoFetcherError,
    PiggybackFetcher,
    ProgramFetcher,
    TCPFetcher,
    TLSConfig,
)
from cmk.fetchers.filecache import (
    AgentFileCache,
    FileCache,
    FileCacheMode,
    FileCacheOptions,
    MaxAge,
    NoCache,
    SNMPFileCache,
)
from cmk.helper_interface import AgentRawData, FetcherType, SourceInfo, SourceType
from cmk.snmplib import SNMPRawData

from ._api import Source

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


class FetcherFactory(Protocol):
    def make_snmp_fetcher(
        self,
        plugins: AgentBasedPlugins,
        host_name: HostName,
        host_ip_family: Literal[socket.AddressFamily.AF_INET, socket.AddressFamily.AF_INET6],
        ipaddress: HostAddress,
        *,
        source_type: SourceType,
    ) -> Fetcher: ...

    def make_ipmi_fetcher(
        self,
        host_name: HostName,
        ipaddress: HostAddress,
    ) -> IPMIFetcher: ...

    def make_program_fetcher(
        self,
        host_name: HostName,
        host_ip_family: Literal[socket.AddressFamily.AF_INET, socket.AddressFamily.AF_INET6],
        ipaddress: HostAddress | None,
        *,
        program: str,
        stdin: str | None,
    ) -> ProgramFetcher: ...

    def make_tcp_fetcher(
        self,
        host_name: HostName,
        host_ip_family: Literal[socket.AddressFamily.AF_INET, socket.AddressFamily.AF_INET6],
        ipaddress: HostAddress,
        *,
        tls_config: TLSConfig,
    ) -> TCPFetcher: ...

    def make_special_agent_fetcher(
        self,
        *,
        stdin: str | None,
        cmdline: str,
    ) -> ProgramFetcher: ...

    def make_piggyback_fetcher(
        self,
    ) -> PiggybackFetcher: ...


class SNMPSource(Source[SNMPRawData]):
    fetcher_type: Final = FetcherType.SNMP
    source_type: Final = SourceType.HOST

    def __init__(
        self,
        factory: FetcherFactory,
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
        self.factory: Final = factory
        self.plugins: Final = plugins
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
        return self.factory.make_snmp_fetcher(
            self.plugins,
            self.host_name,
            self.host_ip_family,
            self.ipaddress,
            source_type=self.source_type,
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
        factory: FetcherFactory,
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
        self.factory: Final = factory
        self.plugins: Final = plugins
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
        return self.factory.make_snmp_fetcher(
            self.plugins,
            self.host_name,
            self.host_ip_family,
            self.ipaddress,
            source_type=self.source_type,
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
        factory: FetcherFactory,
        host_name: HostName,
        ipaddress: HostAddress,
        *,
        max_age: MaxAge,
        file_cache_path_base: Path,
        file_cache_path_relative: Path,
    ) -> None:
        super().__init__()
        self.factory: Final = factory
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
        return self.factory.make_ipmi_fetcher(self.host_name, self.ipaddress)

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
        factory: FetcherFactory,
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
        self.factory: Final = factory
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
        return self.factory.make_program_fetcher(
            self.host_name, self.host_ip_family, self.ipaddress, program=self.program, stdin=None
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
            file_cache_mode=(
                # Careful: at most read-only!
                FileCacheMode.DISABLED if file_cache_options.disabled else FileCacheMode.READ
            ),
        )


class TCPSource(Source[AgentRawData]):
    fetcher_type: Final = FetcherType.TCP
    source_type: Final = SourceType.HOST

    def __init__(
        self,
        factory: FetcherFactory,
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
        self.factory: Final = factory
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
        return self.factory.make_tcp_fetcher(
            self.host_name,
            self.host_ip_family,
            self.ipaddress,
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
        factory: FetcherFactory,
        host_name: HostName,
        ipaddress: HostAddress | None,
        *,
        max_age: MaxAge,
        agent_name: str,
        stdin: str | None,
        cmdline: str,
        file_cache_path_base: Path,
        file_cache_path_relative: Path,
    ) -> None:
        super().__init__()
        self.factory: Final = factory
        self.host_name: Final = host_name
        self.ipaddress: Final = ipaddress
        self._max_age: Final = max_age
        self._agent_name: Final = agent_name
        self._stdin: Final = stdin
        self._cmdline: Final = cmdline
        self._file_cache_path_base: Final = file_cache_path_base
        self._file_cache_path_relative: Final = file_cache_path_relative

    def source_info(self) -> SourceInfo:
        return SourceInfo(
            self.host_name,
            self.ipaddress,
            f"special_{self._agent_name}",
            self.fetcher_type,
            self.source_type,
        )

    def fetcher(self) -> ProgramFetcher:
        return self.factory.make_special_agent_fetcher(
            cmdline=self._cmdline,
            stdin=self._stdin,
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
        factory: FetcherFactory,
        host_name: HostName,
        ipaddress: HostAddress | None,
    ) -> None:
        super().__init__()
        self.factory: Final = factory
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
        self, *, simulation: bool, file_cache_options: FileCacheOptions
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

    def file_cache(self, *, simulation: bool, file_cache_options: FileCacheOptions) -> FileCache:
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

    def file_cache(self, *, simulation: bool, file_cache_options: FileCacheOptions) -> FileCache:
        return _NO_CACHE


class MetricBackendSource(Source[AgentRawData]):
    fetcher_type: Final = FetcherType.SPECIAL_AGENT
    source_type: Final = SourceType.HOST

    def __init__(
        self,
        fetcher: Fetcher[AgentRawData],
        host_name: HostName,
        ipaddress: HostAddress | None,
        *,
        max_age: MaxAge,
        file_cache_path_base: Path,
        file_cache_path_relative: Path,
    ) -> None:
        super().__init__()
        self._fetcher: Final = fetcher
        self.host_name: Final = host_name
        self.ipaddress: Final = ipaddress
        self._max_age: Final = max_age
        self._file_cache_path_base: Final = file_cache_path_base
        self._file_cache_path_relative: Final = file_cache_path_relative

    def source_info(self) -> SourceInfo:
        return SourceInfo(
            self.host_name,
            self.ipaddress,
            "special_otel",  # TODO: metric backend
            self.fetcher_type,
            self.source_type,
        )

    def fetcher(self) -> Fetcher[AgentRawData]:
        return self._fetcher

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
            use_only_cache=False,
            file_cache_mode=FileCacheMode.DISABLED,
        )
