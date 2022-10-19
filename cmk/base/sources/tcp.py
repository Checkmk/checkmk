#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import socket
from pathlib import Path
from typing import Final, Literal, Mapping, Optional

from cmk.utils.type_defs import AgentRawData, HostAddress, HostName, SourceType

import cmk.core_helpers.cache as file_cache
from cmk.core_helpers import FetcherType, TCPFetcher
from cmk.core_helpers.agent import AgentFileCache, AgentRawDataSection
from cmk.core_helpers.cache import FileCacheGlobals

from ._abstract import Source


class TCPSource(Source[AgentRawData, AgentRawDataSection]):
    def __init__(
        self,
        hostname: HostName,
        ipaddress: Optional[HostAddress],
        *,
        source_type: SourceType,
        fetcher_type: FetcherType,
        id_: Literal["agent"],
        cache_dir: Path,
        simulation_mode: bool,
        address_family: socket.AddressFamily,
        agent_port: int,
        tcp_connect_timeout: float,
        agent_encryption: Mapping[str, str],
        file_cache_max_age: file_cache.MaxAge,
    ) -> None:
        super().__init__(
            hostname,
            ipaddress,
            source_type=source_type,
            fetcher_type=fetcher_type,
            id_=id_,
        )
        self.file_cache_base_path: Final = cache_dir
        self.simulation_mode: Final = simulation_mode
        self.file_cache_max_age: Final = file_cache_max_age

        self.agent_port: Final = agent_port
        self.address_family: Final = address_family
        self.tcp_connect_timeout: Final = tcp_connect_timeout
        self.agent_encryption: Final = agent_encryption

    def _make_file_cache(self) -> AgentFileCache:
        return AgentFileCache(
            self.hostname,
            path_template="",
            max_age=self.file_cache_max_age,
            use_outdated=self.simulation_mode or FileCacheGlobals.use_outdated,
            simulation=self.simulation_mode,
            use_only_cache=FileCacheGlobals.tcp_use_only_cache,
            file_cache_mode=FileCacheGlobals.file_cache_mode(),
        )

    def _make_fetcher(self) -> TCPFetcher:
        return TCPFetcher(
            ident=self.id,
            family=self.address_family,
            address=(self.ipaddress, self.agent_port),
            host_name=self.hostname,
            timeout=self.tcp_connect_timeout,
            encryption_settings=self.agent_encryption,
        )
