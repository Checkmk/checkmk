#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import socket
from typing import Optional

from cmk.utils.type_defs import AgentRawData, HostAddress, HostName, SourceType

from cmk.fetchers import FetcherType, TCPFetcher

import cmk.base.ip_lookup as ip_lookup
from cmk.base.config import HostConfig, SelectedRawSections
from cmk.base.exceptions import MKAgentError

from ._abstract import Mode
from .agent import AgentConfigurator, AgentDataSource, AgentSummarizerDefault


class TCPConfigurator(AgentConfigurator):
    _use_only_cache = False

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
            description=TCPConfigurator._make_description(hostname, ipaddress),
            id_="agent",
            cpu_tracking_id="agent",
            main_data_source=main_data_source,
        )
        self.port: Optional[int] = None
        self.timeout: Optional[float] = None

    def configure_fetcher(self):
        ip_lookup.verify_ipaddress(self.ipaddress)
        assert self.ipaddress

        return {
            "family": socket.AF_INET6 if self.host_config.is_ipv6_primary else socket.AF_INET,
            "address": (self.ipaddress, self.port or self.host_config.agent_port),
            "timeout": self.timeout or self.host_config.tcp_connect_timeout,
            "encryption_settings": self.host_config.agent_encryption,
        }

    def make_checker(self) -> "TCPDataSource":
        return TCPDataSource(self)

    @staticmethod
    def _make_description(hostname: HostName, ipaddress: Optional[HostAddress]) -> str:
        return "TCP: %s:%d" % (
            ipaddress,
            HostConfig.make_host_config(hostname).agent_port,
        )


class TCPDataSource(AgentDataSource):
    def __init__(self, configurator: TCPConfigurator) -> None:
        super().__init__(
            configurator,
            summarizer=AgentSummarizerDefault(configurator),
        )

    def _execute(
        self,
        *,
        selected_raw_sections: Optional[SelectedRawSections],
    ) -> AgentRawData:
        if TCPConfigurator._use_only_cache:
            raise MKAgentError("Got no data: No usable cache file present at %s" %
                               self.configurator.file_cache.path)

        with TCPFetcher.from_json(self.configurator.configure_fetcher()) as fetcher:
            return fetcher.data()
        raise MKAgentError("Failed to read data")

    @staticmethod
    def use_only_cache() -> None:
        TCPConfigurator._use_only_cache = True
