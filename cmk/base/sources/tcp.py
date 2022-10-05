#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import socket
from typing import Final, Literal, Mapping, Optional

from cmk.utils.translations import TranslationOptions
from cmk.utils.type_defs import ExitSpec, HostAddress, HostName, SourceType

import cmk.core_helpers.cache as file_cache
from cmk.core_helpers import FetcherType, TCPFetcher
from cmk.core_helpers.agent import AgentFileCache, AgentSummarizerDefault
from cmk.core_helpers.cache import FileCacheGlobals, FileCacheMode

from .agent import AgentSource


class TCPSource(AgentSource):
    def __init__(
        self,
        hostname: HostName,
        ipaddress: Optional[HostAddress],
        *,
        id_: Literal["agent"],
        main_data_source: bool,
        simulation_mode: bool,
        agent_simulator: bool,
        translation: TranslationOptions,
        encoding_fallback: str,
        check_interval: int,
        address_family: socket.AddressFamily,
        agent_port: int,
        tcp_connect_timeout: float,
        agent_encryption: Mapping[str, str],
        file_cache_max_age: file_cache.MaxAge,
    ) -> None:
        super().__init__(
            hostname,
            ipaddress,
            source_type=SourceType.HOST,
            fetcher_type=FetcherType.TCP,
            id_=id_,
            main_data_source=main_data_source,
            simulation_mode=simulation_mode,
            agent_simulator=agent_simulator,
            translation=translation,
            encoding_fallback=encoding_fallback,
            check_interval=check_interval,
            file_cache_max_age=file_cache_max_age,
        )
        self.agent_port: Final = agent_port
        self.address_family: Final = address_family
        self.tcp_connect_timeout: Final = tcp_connect_timeout
        self.agent_encryption: Final = agent_encryption

        # TODO(ml): These two options ought to be static as well!
        self.port: Optional[int] = None
        self.timeout: Optional[float] = None

    def _make_file_cache(self) -> AgentFileCache:
        return AgentFileCache(
            self.hostname,
            base_path=self.file_cache_base_path,
            max_age=self.file_cache_max_age,
            use_outdated=self.simulation_mode or FileCacheGlobals.use_outdated,
            simulation=self.simulation_mode,
            use_only_cache=FileCacheGlobals.tcp_use_only_cache,
            file_cache_mode=FileCacheMode.DISABLED
            if FileCacheGlobals.disabled
            else FileCacheMode.READ_WRITE,
        )

    def _make_fetcher(self) -> TCPFetcher:
        return TCPFetcher(
            family=self.address_family,
            address=(self.ipaddress, self.port or self.agent_port),
            host_name=self.hostname,
            timeout=self.timeout or self.tcp_connect_timeout,
            encryption_settings=self.agent_encryption,
        )

    def _make_summarizer(self, *, exit_spec: ExitSpec) -> AgentSummarizerDefault:
        return AgentSummarizerDefault(exit_spec)
