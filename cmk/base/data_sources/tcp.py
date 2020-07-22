#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import socket
from typing import cast, Optional

from cmk.utils.type_defs import HostAddress, HostName, SourceType

from cmk.fetchers import TCPDataFetcher

import cmk.base.ip_lookup as ip_lookup
from cmk.base.check_utils import RawAgentData
from cmk.base.config import HostConfig, SelectedRawSections
from cmk.base.exceptions import MKAgentError, MKEmptyAgentData

from ._abstract import ABCConfigurator
from .agent import AgentDataSource


class TCPConfigurator(ABCConfigurator):
    _use_only_cache = False

    def __init__(
        self,
        hostname: HostName,
        ipaddress: Optional[HostAddress],
    ) -> None:
        super().__init__(
            hostname,
            ipaddress,
            source_type=SourceType.HOST,
            description=TCPConfigurator._make_description(hostname, ipaddress),
            id_="agent",
            cpu_tracking_id="agent",
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

    @staticmethod
    def _make_description(hostname: HostName, ipaddress: Optional[HostAddress]) -> str:
        return "TCP: %s:%d" % (
            ipaddress,
            HostConfig.make_host_config(hostname).agent_port,
        )


class TCPDataSource(AgentDataSource):
    def _execute(
        self,
        *,
        selected_raw_sections: Optional[SelectedRawSections],
    ) -> RawAgentData:
        if TCPConfigurator._use_only_cache:
            raise MKAgentError("Got no data: No usable cache file present at %s" %
                               self._cache_file_path())

        with TCPDataFetcher.from_json(self.configurator.configure_fetcher()) as fetcher:
            output = fetcher.data()
            # TODO(ml): Get rid of the `cast` by moving the error hanling to the fetcher.
            configurator = cast(TCPConfigurator, self.configurator)
            if not output:  # may be caused by xinetd not allowing our address
                raise MKEmptyAgentData("Empty output from agent at %s:%d" % (
                    configurator.ipaddress,
                    configurator.port or self.configurator.host_config.agent_port,
                ))
            if len(output) < 16:
                raise MKAgentError("Too short output from agent: %r" % output)
            return output
        raise MKAgentError("Failed to read data")

    def describe(self) -> str:
        return self.configurator.description

    @staticmethod
    def use_only_cache() -> None:
        TCPConfigurator._use_only_cache = True
