#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import socket
from typing import Dict, Optional

from cmk.utils.type_defs import HostAddress, HostName, SectionName

from cmk.fetchers import TCPDataFetcher

from cmk.base.api.agent_based.section_types import AgentSectionPlugin
from cmk.base.check_utils import RawAgentData
from cmk.base.config import SectionPlugin
from cmk.base.exceptions import MKAgentError, MKEmptyAgentData
import cmk.base.ip_lookup as ip_lookup

from .agent import AgentDataSource

#.
#   .--Agent---------------------------------------------------------------.
#   |                        _                    _                        |
#   |                       / \   __ _  ___ _ __ | |_                      |
#   |                      / _ \ / _` |/ _ \ '_ \| __|                     |
#   |                     / ___ \ (_| |  __/ | | | |_                      |
#   |                    /_/   \_\__, |\___|_| |_|\__|                     |
#   |                            |___/                                     |
#   +----------------------------------------------------------------------+
#   | Real communication with the target system.                           |
#   '----------------------------------------------------------------------'


class TCPDataSource(AgentDataSource):
    _use_only_cache = False

    def __init__(
        self,
        hostname: HostName,
        ipaddress: Optional[HostAddress],
        selected_raw_sections: Optional[Dict[SectionName, SectionPlugin]] = None,
        main_data_source: bool = False,
    ) -> None:
        super(TCPDataSource, self).__init__(
            hostname,
            ipaddress,
            selected_raw_section_names=None if selected_raw_sections is None else
            {s.name for s in selected_raw_sections.values() if isinstance(s, AgentSectionPlugin)},
            main_data_source=main_data_source,
        )
        self._port: Optional[int] = None
        self._timeout: Optional[float] = None

    def id(self) -> str:
        return "agent"

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

    def _execute(self) -> RawAgentData:
        if self._use_only_cache:
            raise MKAgentError("Got no data: No usable cache file present at %s" %
                               self._cache_file_path())

        ip_lookup.verify_ipaddress(self._ipaddress)
        assert self._ipaddress

        with TCPDataFetcher(
                socket.AF_INET6 if self._host_config.is_ipv6_primary else socket.AF_INET,
            (self._ipaddress, self.port),
                self.timeout,
                self._host_config.agent_encryption,
        ) as fetcher:
            output = fetcher.data()
            if not output:  # may be caused by xinetd not allowing our address
                raise MKEmptyAgentData("Empty output from agent at %s:%d" %
                                       (self._ipaddress, self.port))
            if len(output) < 16:
                raise MKAgentError("Too short output from agent: %r" % output)
            return output
        raise MKAgentError("Failed to read data")

    def describe(self) -> str:
        """Return a short textual description of the agent"""
        return "TCP: %s:%d" % (self._ipaddress, self._host_config.agent_port)

    @classmethod
    def use_only_cache(cls) -> None:
        cls._use_only_cache = True
