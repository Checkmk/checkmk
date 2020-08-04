#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, cast, Dict, Final, Optional

from cmk.utils.type_defs import (
    HostAddress,
    HostName,
    RawAgentData,
    SectionName,
    ServiceCheckResult,
    ServiceDetails,
    SourceType,
)

from cmk.fetchers import IPMIDataFetcher

from cmk.base.config import HostConfig, IPMICredentials, SelectedRawSections
from cmk.base.exceptions import MKAgentError

from ._abstract import Mode
from .agent import AgentConfigurator, AgentDataSource, AgentHostSections


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
            description=IPMIConfigurator._make_description(
                ipaddress,
                cast(IPMICredentials,
                     HostConfig.make_host_config(hostname).management_credentials),
            ),
            id_="mgmt_ipmi",
            cpu_tracking_id="mgmt_ipmi",
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
            "address": self.ipaddress,
            "username": self.credentials["username"],
            "password": self.credentials["password"],
        }

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


# NOTE: This class is *not* abstract, even if pylint is too dumb to see that!
class IPMIManagementBoardDataSource(AgentDataSource):
    def _execute(
        self,
        *,
        selected_raw_sections: Optional[SelectedRawSections],
    ) -> RawAgentData:
        if selected_raw_sections is None:
            # pylint: disable=unused-variable
            # TODO(ml): Should we pass that to the fetcher?
            selected_raw_section_names = {SectionName("mgmt_ipmi_sensors")}

        with IPMIDataFetcher.from_json(self.configurator.configure_fetcher()) as fetcher:
            return fetcher.data()
        raise MKAgentError("Failed to read data")

    def _summary_result(self) -> ServiceCheckResult:
        return 0, "Version: %s" % self._get_ipmi_version(self._host_sections), []

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
