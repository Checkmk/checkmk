#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import socket
from typing import Optional

from cmk.utils.type_defs import HostAddress, HostName, SourceType

from cmk.helpers import FetcherType, TCPFetcher
from cmk.helpers.agent import (
    DefaultAgentFileCache,
    DefaultAgentFileCacheFactory,
    AgentSummarizerDefault,
)
from cmk.helpers.type_defs import Mode

import cmk.base.config as config
from cmk.base.config import HostConfig

from .agent import AgentSource


class TCPSource(AgentSource):
    use_only_cache = False

    def __init__(
        self,
        hostname: HostName,
        ipaddress: Optional[HostAddress],
        *,
        mode: Mode,
        main_data_source: bool = False,
    ) -> None:
        super().__init__(
            hostname,
            ipaddress,
            mode=mode,
            source_type=SourceType.HOST,
            fetcher_type=FetcherType.TCP,
            description=TCPSource._make_description(hostname, ipaddress),
            id_="agent",
            main_data_source=main_data_source,
        )
        self.port: Optional[int] = None
        self.timeout: Optional[float] = None

    def _make_file_cache(self) -> DefaultAgentFileCache:
        return DefaultAgentFileCacheFactory(
            path=self.file_cache_path,
            simulation=config.simulation_mode,
            max_age=self.file_cache_max_age,
        ).make()

    def _make_fetcher(self) -> TCPFetcher:
        return TCPFetcher(
            self._make_file_cache(),
            family=socket.AF_INET6 if self.host_config.is_ipv6_primary else socket.AF_INET,
            address=(self.ipaddress, self.port or self.host_config.agent_port),
            timeout=self.timeout or self.host_config.tcp_connect_timeout,
            encryption_settings=self.host_config.agent_encryption,
            use_only_cache=self.use_only_cache,
        )

    def _make_summarizer(self) -> AgentSummarizerDefault:
        return AgentSummarizerDefault(
            self.exit_spec,
            is_cluster=self.host_config.is_cluster,
            agent_min_version=config.agent_min_version,
            agent_target_version=self.host_config.agent_target_version,
            only_from=self.host_config.only_from,
        )

    @staticmethod
    def _make_description(hostname: HostName, ipaddress: Optional[HostAddress]) -> str:
        return "TCP: %s:%d" % (
            ipaddress,
            HostConfig.make_host_config(hostname).agent_port,
        )
