#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import socket
from typing import Optional, Set

from cmk.utils.type_defs import HostAddress, HostName

from cmk.fetchers import TCPDataFetcher

import cmk.base.ip_lookup as ip_lookup
from cmk.base.check_utils import RawAgentData
from cmk.base.config import SectionPlugin
from cmk.base.exceptions import MKAgentError, MKEmptyAgentData

from .agent import AgentDataSource


class TCPDataSource(AgentDataSource):
    _use_only_cache = False

    def __init__(
        self,
        hostname: HostName,
        ipaddress: Optional[HostAddress],
        main_data_source: bool = False,
    ) -> None:
        super(TCPDataSource, self).__init__(
            hostname,
            ipaddress,
            main_data_source=main_data_source,
            id_="agent",
            cpu_tracking_id="agent",
        )
        self._port: Optional[int] = None
        self._timeout: Optional[float] = None

    @property
    def port(self) -> int:
        if self._port is None:
            return self._host_config.agent_port
        return self._port

    @port.setter
    def port(self, value: Optional[int]) -> None:
        self._port = value

    @property
    def timeout(self) -> float:
        if self._timeout is None:
            return self._host_config.tcp_connect_timeout
        return self._timeout

    @timeout.setter
    def timeout(self, value: Optional[float]) -> None:
        self._timeout = value

    def _execute(
        self,
        *,
        selected_sections: Optional[Set[SectionPlugin]],
    ) -> RawAgentData:
        if self._use_only_cache:
            raise MKAgentError("Got no data: No usable cache file present at %s" %
                               self._cache_file_path())

        ip_lookup.verify_ipaddress(self.ipaddress)
        assert self.ipaddress

        with TCPDataFetcher(
                socket.AF_INET6 if self._host_config.is_ipv6_primary else socket.AF_INET,
            (self.ipaddress, self.port),
                self.timeout,
                self._host_config.agent_encryption,
        ) as fetcher:
            output = fetcher.data()
            if not output:  # may be caused by xinetd not allowing our address
                raise MKEmptyAgentData("Empty output from agent at %s:%d" %
                                       (self.ipaddress, self.port))
            if len(output) < 16:
                raise MKAgentError("Too short output from agent: %r" % output)
            return output
        raise MKAgentError("Failed to read data")

    def describe(self) -> str:
        """Return a short textual description of the agent"""
        return "TCP: %s:%d" % (self.ipaddress, self._host_config.agent_port)

    @classmethod
    def use_only_cache(cls) -> None:
        cls._use_only_cache = True
