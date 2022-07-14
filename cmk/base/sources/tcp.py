#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import socket
from typing import Optional

from cmk.utils.translations import TranslationOptions
from cmk.utils.type_defs import HostAddress, SourceType

from cmk.core_helpers import FetcherType, TCPFetcher
from cmk.core_helpers.agent import AgentFileCache, AgentFileCacheFactory, AgentSummarizerDefault

from cmk.base.config import HostConfig

from .agent import AgentSource


class TCPSource(AgentSource):
    # TODO(ml): Global caching options usually go to the FileCacheFactory,
    #           actually, the "factory" has no other purpose than to hold
    #           all of this at one place.  Would it be possible to move this
    #           option there as well?
    use_only_cache = False

    def __init__(
        self,
        host_config: HostConfig,
        ipaddress: Optional[HostAddress],
        *,
        main_data_source: bool = False,
        simulation_mode: bool,
        agent_simulator: bool,
        translation: TranslationOptions,
        encoding_fallback: str,
    ) -> None:
        super().__init__(
            host_config,
            ipaddress,
            source_type=SourceType.HOST,
            fetcher_type=FetcherType.TCP,
            description=TCPSource._make_description(ipaddress, host_config.agent_port),
            id_="agent",
            main_data_source=main_data_source,
            simulation_mode=simulation_mode,
            agent_simulator=agent_simulator,
            translation=translation,
            encoding_fallback=encoding_fallback,
        )
        self.port: Optional[int] = None
        self.timeout: Optional[float] = None

    def _make_file_cache(self) -> AgentFileCache:
        return AgentFileCacheFactory(
            self.host_config.hostname,
            base_path=self.file_cache_base_path,
            simulation=self.simulation_mode,
            use_only_cache=self.use_only_cache,
            max_age=self.file_cache_max_age,
        ).make()

    def _make_fetcher(self) -> TCPFetcher:
        return TCPFetcher(
            family=socket.AF_INET6 if self.host_config.is_ipv6_primary else socket.AF_INET,
            address=(self.ipaddress, self.port or self.host_config.agent_port),
            host_name=self.host_config.hostname,
            timeout=self.timeout or self.host_config.tcp_connect_timeout,
            encryption_settings=self.host_config.agent_encryption,
        )

    def _make_summarizer(self) -> AgentSummarizerDefault:
        return AgentSummarizerDefault(self.exit_spec)

    @staticmethod
    def _make_description(ipaddress: Optional[HostAddress], agent_port: int) -> str:
        return "TCP: %s:%d" % (ipaddress, agent_port)
