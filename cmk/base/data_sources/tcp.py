#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import socket
from typing import Dict, List, Optional, Tuple, Set

from cmk.base.api import PluginName
from cmk.base.api.agent_based.section_types import AgentSectionPlugin
from cmk.base.check_utils import RawAgentData
from cmk.base.config import SectionPlugin
from cmk.base.exceptions import MKAgentError, MKEmptyAgentData
from cmk.fetchers import TCPDataFetcher
from cmk.utils.type_defs import HostName, HostAddress

from .abstract import CheckMKAgentDataSource, verify_ipaddress

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


class TCPDataSource(CheckMKAgentDataSource):
    _use_only_cache = False

    def __init__(
            self,
            hostname,  # type: HostName
            ipaddress,  # type: Optional[HostAddress]
            selected_raw_sections=None,  # type: Optional[Dict[PluginName, SectionPlugin]]
    ):
        # type: (...) -> None
        super(TCPDataSource, self).__init__(
            hostname,
            ipaddress,
            None if selected_raw_sections is None else
            {s.name for s in selected_raw_sections.values() if isinstance(s, AgentSectionPlugin)},
        )
        self._port = None  # type: Optional[int]
        self._timeout = None  # type: Optional[float]

    def id(self):
        # type: () -> str
        return "agent"

    @property
    def port(self):
        # type: () -> int
        if self._port is None:
            return self._host_config.agent_port
        return self._port

    @port.setter
    def port(self, value):
        # type: (Optional[int]) -> None
        self._port = value

    @property
    def timeout(self):
        # type: () -> float
        if self._timeout is None:
            return self._host_config.tcp_connect_timeout
        return self._timeout

    @timeout.setter
    def timeout(self, value):
        # type: (Optional[float]) -> None
        self._timeout = value

    def _execute(self):
        # type: () -> RawAgentData
        if self._use_only_cache:
            raise MKAgentError("Got no data: No usable cache file present at %s" %
                               self._cache_file_path())

        verify_ipaddress(self._ipaddress)
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

    def describe(self):
        # type: () -> str
        """Return a short textual description of the agent"""
        return "TCP: %s:%d" % (self._ipaddress, self._host_config.agent_port)

    @classmethod
    def use_only_cache(cls):
        # type: () -> None
        cls._use_only_cache = True
