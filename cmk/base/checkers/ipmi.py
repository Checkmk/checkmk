#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import cast, Final, Optional

from cmk.utils.type_defs import (
    HostAddress,
    HostName,
    SectionName,
    ServiceCheckResult,
    ServiceDetails,
    SourceType,
)

from cmk.fetchers import IPMIFetcher, FetcherType
from cmk.fetchers.agent import DefaultAgentFileCache

import cmk.base.config as config
from cmk.base.config import HostConfig, IPMICredentials
from cmk.base.exceptions import MKAgentError

from ._abstract import Mode
from .agent import AgentSource, AgentHostSections, AgentSummarizer, DefaultAgentFileCacheFactory


class IPMISource(AgentSource):
    def __init__(
        self,
        hostname: HostName,
        ipaddress: Optional[HostAddress],
        *,
        mode: Mode,
    ):
        super().__init__(
            hostname,
            ipaddress,
            mode=mode,
            source_type=SourceType.MANAGEMENT,
            fetcher_type=FetcherType.IPMI,
            description=IPMISource._make_description(
                ipaddress,
                cast(IPMICredentials,
                     HostConfig.make_host_config(hostname).management_credentials),
            ),
            id_="mgmt_ipmi",
            cpu_tracking_id="mgmt_ipmi",
            main_data_source=False,
        )
        self.credentials: Final[IPMICredentials] = cast(
            IPMICredentials,
            HostConfig.make_host_config(hostname).management_credentials)

    def _make_file_cache(self) -> DefaultAgentFileCache:
        return DefaultAgentFileCacheFactory(
            path=self.file_cache_path,
            simulation=config.simulation_mode,
            max_age=self.file_cache_max_age,
        ).make()

    def _make_fetcher(self) -> IPMIFetcher:
        if not self.credentials:
            raise MKAgentError("Missing credentials")

        if self.ipaddress is None:
            raise MKAgentError("Missing IP address")

        return IPMIFetcher(
            self._make_file_cache(),
            address=self.ipaddress,
            username=self.credentials["username"],
            password=self.credentials["password"],
        )

    def _make_summarizer(self) -> "IPMISummarizer":
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


class IPMISummarizer(AgentSummarizer):
    def _summarize(self, host_sections: AgentHostSections) -> ServiceCheckResult:
        return 0, "Version: %s" % self._get_ipmi_version(host_sections), []

    @staticmethod
    def _get_ipmi_version(host_sections: Optional[AgentHostSections]) -> ServiceDetails:
        if host_sections is None:
            return "unknown"

        section = host_sections.sections.get(SectionName("mgmt_ipmi_firmware"))
        if not section:
            return "unknown"

        for line in section:
            if line[0] == "BMC Version" and line[1] == "version":
                return line[2]

        return "unknown"
