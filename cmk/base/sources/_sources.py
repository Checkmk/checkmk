#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# TODO This module should be freed from base deps.

from collections.abc import Mapping
from typing import Final

from cmk.utils.agentdatatype import AgentRawData
from cmk.utils.exceptions import OnError
from cmk.utils.hostaddress import HostAddress, HostName

from cmk.snmplib.type_defs import SNMPRawData

from cmk.fetchers import Fetcher, FetcherType, NoFetcher, NoFetcherError, ProgramFetcher
from cmk.fetchers.config import make_file_cache_path_template
from cmk.fetchers.filecache import (
    AgentFileCache,
    FileCache,
    FileCacheMode,
    FileCacheOptions,
    MaxAge,
    NoCache,
    SNMPFileCache,
)

from cmk.checkengine import SourceInfo, SourceType
from cmk.checkengine.type_defs import SectionNameCollection

import cmk.base.config as config
import cmk.base.core_config as core_config
from cmk.base.config import ConfigCache

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


class SNMPSource(Source[SNMPRawData]):
    fetcher_type: Final = FetcherType.SNMP
    source_type: Final = SourceType.HOST

    def __init__(
        self,
        config_cache: ConfigCache,
        host_name: HostName,
        ipaddress: HostAddress,
        *,
        max_age: MaxAge,
        on_scan_error: OnError,
        selected_sections: SectionNameCollection,
    ) -> None:
        super().__init__()
        self.config_cache: Final = config_cache
        self.host_name: Final = host_name
        self.ipaddress: Final = ipaddress
        self._max_age: Final = max_age
        self._on_scan_error: Final = on_scan_error
        self._selected_sections: Final = selected_sections

    def source_info(self) -> SourceInfo:
        return SourceInfo(
            self.host_name,
            self.ipaddress,
            "snmp",
            self.fetcher_type,
            self.source_type,
        )

    def fetcher(self) -> Fetcher[SNMPRawData]:
        return self.config_cache.make_snmp_fetcher(
            self.host_name,
            self.ipaddress,
            snmp_config=self.config_cache.make_snmp_config(
                self.host_name, self.ipaddress, SourceType.HOST
            ),
            on_scan_error=self._on_scan_error,
            selected_sections=self._selected_sections,
        )

    def file_cache(
        self, *, simulation: bool, file_cache_options: FileCacheOptions
    ) -> FileCache[SNMPRawData]:
        return SNMPFileCache(
            self.host_name,
            path_template=make_file_cache_path_template(
                fetcher_type=self.fetcher_type,
                ident=self.source_info().ident,
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
        config_cache: ConfigCache,
        host_name: HostName,
        ipaddress: HostAddress,
        *,
        max_age: MaxAge,
        on_scan_error: OnError,
        selected_sections: SectionNameCollection,
    ) -> None:
        super().__init__()
        self.config_cache: Final = config_cache
        self.host_name: Final = host_name
        self.ipaddress: Final = ipaddress
        self._max_age: Final = max_age
        self._on_scan_error: Final = on_scan_error
        self._selected_sections: Final = selected_sections

    def source_info(self) -> SourceInfo:
        return SourceInfo(
            self.host_name,
            self.ipaddress,
            "mgmt_snmp",
            self.fetcher_type,
            self.source_type,
        )

    def fetcher(self) -> Fetcher[SNMPRawData]:
        return self.config_cache.make_snmp_fetcher(
            self.host_name,
            self.ipaddress,
            snmp_config=self.config_cache.make_snmp_config(
                self.host_name, self.ipaddress, SourceType.MANAGEMENT
            ),
            on_scan_error=self._on_scan_error,
            selected_sections=self._selected_sections,
        )

    def file_cache(
        self, *, simulation: bool, file_cache_options: FileCacheOptions
    ) -> FileCache[SNMPRawData]:
        return SNMPFileCache(
            self.host_name,
            path_template=make_file_cache_path_template(
                fetcher_type=self.fetcher_type, ident=self.source_info().ident
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
        config_cache: ConfigCache,
        host_name: HostName,
        ipaddress: HostAddress,
        *,
        max_age: MaxAge,
    ) -> None:
        super().__init__()
        self.config_cache: Final = config_cache
        self.host_name: Final = host_name
        self.ipaddress: Final = ipaddress
        self._max_age: Final = max_age

    def source_info(self) -> SourceInfo:
        return SourceInfo(
            self.host_name,
            self.ipaddress,
            "mgmt_ipmi",
            self.fetcher_type,
            self.source_type,
        )

    def fetcher(self) -> Fetcher[AgentRawData]:
        return self.config_cache.make_ipmi_fetcher(self.host_name, self.ipaddress)

    def file_cache(
        self, *, simulation: bool, file_cache_options: FileCacheOptions
    ) -> FileCache[AgentRawData]:
        return AgentFileCache(
            self.host_name,
            path_template=make_file_cache_path_template(
                fetcher_type=self.fetcher_type, ident=self.source_info().ident
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
        config_cache: ConfigCache,
        host_name: HostName,
        ipaddress: HostAddress | None,
        *,
        max_age: MaxAge,
    ) -> None:
        super().__init__()
        self.config_cache: Final = config_cache
        self.host_name: Final = host_name
        self.ipaddress: Final = ipaddress
        self._max_age: Final = max_age
        # `make_program_commandline()` may raise LookupError if no datasource
        # is configured.
        self._cmdline: Final = self.config_cache.make_program_commandline(host_name, ipaddress)
        self._stdin: Final = None
        self._is_cmc: Final = config.is_cmc()

    def source_info(self) -> SourceInfo:
        return SourceInfo(
            self.host_name,
            self.ipaddress,
            "agent",
            self.fetcher_type,
            self.source_type,
        )

    def fetcher(self) -> Fetcher[AgentRawData]:
        return ProgramFetcher(cmdline=self._cmdline, stdin=self._stdin, is_cmc=self._is_cmc)

    def file_cache(
        self, *, simulation: bool, file_cache_options: FileCacheOptions
    ) -> FileCache[AgentRawData]:
        return AgentFileCache(
            self.host_name,
            path_template=make_file_cache_path_template(
                fetcher_type=self.fetcher_type, ident=self.source_info().ident
            ),
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
    ) -> None:
        super().__init__()
        self.host_name: Final = host_name
        self.ipaddress: Final = ipaddress
        self._max_age: Final = max_age

    def source_info(self) -> SourceInfo:
        return SourceInfo(
            self.host_name,
            self.ipaddress,
            "push-agent",
            self.fetcher_type,
            self.source_type,
        )

    def fetcher(self) -> Fetcher[AgentRawData]:
        return NoFetcher(NoFetcherError.NO_FETCHER)

    def file_cache(
        self, *, simulation: bool, file_cache_options: FileCacheOptions
    ) -> FileCache[AgentRawData]:
        return AgentFileCache(
            self.host_name,
            path_template=make_file_cache_path_template(
                fetcher_type=self.fetcher_type, ident=self.source_info().ident
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
                FileCacheMode.DISABLED
                if file_cache_options.disabled
                else FileCacheMode.READ
            ),
        )


class TCPSource(Source[AgentRawData]):
    fetcher_type: Final = FetcherType.TCP
    source_type: Final = SourceType.HOST

    def __init__(
        self,
        config_cache: ConfigCache,
        host_name: HostName,
        ipaddress: HostAddress,
        *,
        max_age: MaxAge,
    ) -> None:
        super().__init__()
        self.config_cache: Final = config_cache
        self.host_name: Final = host_name
        self.ipaddress: Final = ipaddress
        self._max_age: Final = max_age

    def source_info(self) -> SourceInfo:
        return SourceInfo(
            self.host_name,
            self.ipaddress,
            "agent",
            self.fetcher_type,
            self.source_type,
        )

    def fetcher(self) -> Fetcher[AgentRawData]:
        return self.config_cache.make_tcp_fetcher(self.host_name, self.ipaddress)

    def file_cache(
        self, *, simulation: bool, file_cache_options: FileCacheOptions
    ) -> FileCache[AgentRawData]:
        return AgentFileCache(
            self.host_name,
            path_template=make_file_cache_path_template(
                fetcher_type=self.fetcher_type, ident=self.source_info().ident
            ),
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
        config_cache: ConfigCache,
        host_name: HostName,
        ipaddress: HostAddress | None,
        *,
        max_age: MaxAge,
        agent_name: str,
        params: Mapping[str, object],
    ) -> None:
        super().__init__()
        self.config_cache: Final = config_cache
        self.host_name: Final = host_name
        self.ipaddress: Final = ipaddress
        self._max_age: Final = max_age
        self._agent_name: Final = agent_name
        self._params: Final = params

    def source_info(self) -> SourceInfo:
        return SourceInfo(
            self.host_name,
            self.ipaddress,
            f"special_{self._agent_name}",
            self.fetcher_type,
            self.source_type,
        )

    def fetcher(self) -> Fetcher[AgentRawData]:
        return ProgramFetcher(
            cmdline=self.config_cache.make_special_agent_cmdline(
                self.host_name,
                self.ipaddress,
                self._agent_name,
                self._params,
            ),
            stdin=core_config.make_special_agent_stdin(
                self.host_name,
                self.ipaddress,
                self._agent_name,
                self._params,
            ),
            is_cmc=config.is_cmc(),
        )

    def file_cache(
        self, *, simulation: bool, file_cache_options: FileCacheOptions
    ) -> FileCache[AgentRawData]:
        return AgentFileCache(
            self.host_name,
            path_template=make_file_cache_path_template(
                fetcher_type=self.fetcher_type, ident=self.source_info().ident
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
        config_cache: ConfigCache,
        host_name: HostName,
        ipaddress: HostAddress | None,
    ) -> None:
        super().__init__()
        self.config_cache: Final = config_cache
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

    def fetcher(self) -> Fetcher[AgentRawData]:
        return self.config_cache.make_piggyback_fetcher(self.host_name, self.ipaddress)

    def file_cache(
        self, *, simulation: bool, file_cache_options: FileCacheOptions
    ) -> FileCache[AgentRawData]:
        return NoCache(self.host_name)


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

    def fetcher(self) -> Fetcher:
        return NoFetcher(NoFetcherError.MISSING_IP)

    def file_cache(self, *, simulation: bool, file_cache_options: FileCacheOptions) -> FileCache:
        return NoCache(self.host_name)


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

    def fetcher(self) -> Fetcher:
        return NoFetcher(NoFetcherError.NO_FETCHER)

    def file_cache(self, *, simulation: bool, file_cache_options: FileCacheOptions) -> FileCache:
        return NoCache(self.host_name)
