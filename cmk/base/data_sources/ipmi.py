#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, cast, Dict, Final, Optional

from cmk.utils.type_defs import (
    AgentRawData,
    HostAddress,
    HostName,
    SectionName,
    ServiceCheckResult,
    ServiceDetails,
    SourceType,
)

from cmk.fetchers import FetcherType, IPMIFetcher

from cmk.base.config import HostConfig, IPMICredentials, SelectedRawSections
from cmk.base.exceptions import MKAgentError

from ._abstract import Mode
from .agent import AgentConfigurator, AgentDataSource, AgentHostSections, AgentSummarizer


class IPMIConfigurator(AgentConfigurator):
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
            description=IPMIConfigurator._make_description(
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

    def configure_fetcher(self) -> Dict[str, Any]:
        if not self.credentials:
            raise MKAgentError("Missing credentials")

        if self.ipaddress is None:
            raise MKAgentError("Missing IP address")

        return {
            "file_cache": self.file_cache.configure(),
            "address": self.ipaddress,
            "username": self.credentials["username"],
            "password": self.credentials["password"],
        }

    def make_checker(self) -> "IPMIManagementBoardDataSource":
        return IPMIManagementBoardDataSource(self)

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
    def summarize(self, host_sections: AgentHostSections) -> ServiceCheckResult:
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


# NOTE: This class is *not* abstract, even if pylint is too dumb to see that!
class IPMIManagementBoardDataSource(AgentDataSource):
    def __init__(self, configurator: IPMIConfigurator) -> None:
        super().__init__(configurator, summarizer=IPMISummarizer())

    def _execute(
        self,
        *,
        selected_raw_sections: Optional[SelectedRawSections],
    ) -> AgentRawData:
        if selected_raw_sections is None:
            # pylint: disable=unused-variable
            # TODO(ml): Should we pass that to the fetcher?
            selected_raw_section_names = {SectionName("mgmt_ipmi_sensors")}

        with IPMIFetcher.from_json(self.configurator.configure_fetcher()) as fetcher:
            return fetcher.fetch()
        raise MKAgentError("Failed to read data")
