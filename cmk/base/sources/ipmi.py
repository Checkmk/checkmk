#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import cast, Final, Optional

from cmk.utils.exceptions import MKAgentError
from cmk.utils.type_defs import HostAddress, HostName, SourceType

from cmk.core_helpers import FetcherType, IPMIFetcher
from cmk.core_helpers.agent import DefaultAgentFileCache, DefaultAgentFileCacheFactory
from cmk.core_helpers.ipmi import IPMISummarizer

import cmk.base.config as config
from cmk.base.config import HostConfig, IPMICredentials

from .agent import AgentSource


class IPMISource(AgentSource):
    def __init__(self, hostname: HostName, ipaddress: Optional[HostAddress]) -> None:
        super().__init__(
            hostname,
            ipaddress,
            source_type=SourceType.MANAGEMENT,
            fetcher_type=FetcherType.IPMI,
            description=IPMISource._make_description(
                ipaddress,
                cast(IPMICredentials, HostConfig.make_host_config(hostname).management_credentials),
            ),
            id_="mgmt_ipmi",
            main_data_source=False,
        )
        self.credentials: Final[IPMICredentials] = self.get_ipmi_credentials(
            HostConfig.make_host_config(hostname)
        )

    @staticmethod
    def get_ipmi_credentials(host_config: HostConfig) -> IPMICredentials:
        credentials = host_config.management_credentials
        if credentials is None:
            return {}
        # The cast is required because host_config.management_credentials
        # has type `Union[None, str, Tuple[str, ...], Dict[str, str]]`
        return cast(IPMICredentials, credentials)

    def _make_file_cache(self) -> DefaultAgentFileCache:
        return DefaultAgentFileCacheFactory(
            self.hostname,
            base_path=self.file_cache_base_path,
            simulation=config.simulation_mode,
            max_age=self.file_cache_max_age,
        ).make()

    def _make_fetcher(self) -> IPMIFetcher:
        if self.ipaddress is None:
            raise MKAgentError("Missing IP address")

        return IPMIFetcher(
            self._make_file_cache(),
            address=self.ipaddress,
            username=self.credentials.get("username"),
            password=self.credentials.get("password"),
        )

    def _make_summarizer(self) -> IPMISummarizer:
        return IPMISummarizer(self.exit_spec)

    @staticmethod
    def _make_description(ipaddress: Optional[HostAddress], credentials: IPMICredentials):
        description = "Management board - IPMI"
        items = []
        if ipaddress:
            items.append("Address: %s" % ipaddress)
        if credentials:
            items.append("User: %s" % credentials["username"])
        if items:
            description = "%s (%s)" % (description, ", ".join(items))
        return description
