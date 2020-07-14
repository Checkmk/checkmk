#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import cast, Dict, Final, Optional

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

from cmk.base.config import IPMICredentials, SectionPlugin
from cmk.base.exceptions import MKAgentError

from .agent import AgentDataSource


# NOTE: This class is *not* abstract, even if pylint is too dumb to see that!
class IPMIManagementBoardDataSource(AgentDataSource):
    source_type = SourceType.MANAGEMENT

    _raw_sections = {SectionName("mgmt_ipmi_sensors")}

    def __init__(
        self,
        hostname: HostName,
        ipaddress: Optional[HostAddress],
        selected_raw_sections: Optional[Dict[SectionName, SectionPlugin]] = None,
        main_data_source: bool = False,
    ) -> None:
        super(IPMIManagementBoardDataSource, self).__init__(
            hostname,
            ipaddress,
            selected_raw_section_names=None
            if selected_raw_sections is None else self._raw_sections,
            main_data_source=main_data_source,
            id_="mgmt_ipmi",
            cpu_tracking_id="mgmt_ipmi",
        )
        self._credentials = cast(IPMICredentials, self._host_config.management_credentials)
        self.title: Final[str] = "Management board - IPMI"

    def describe(self) -> str:
        items = []
        if self.ipaddress:
            items.append("Address: %s" % self.ipaddress)
        if self._credentials:
            items.append("User: %s" % self._credentials["username"])
        return "%s (%s)" % (self.title, ", ".join(items))

    def _execute(self) -> RawAgentData:
        if not self._credentials:
            raise MKAgentError("Missing credentials")

        if self.ipaddress is None:
            raise MKAgentError("Missing IP address")

        with IPMIDataFetcher(self.ipaddress, self._credentials["username"],
                             self._credentials["password"]) as fetcher:
            return fetcher.data()
        raise MKAgentError("Failed to read data")

    def _summary_result(self, for_checking: bool) -> ServiceCheckResult:
        return 0, "Version: %s" % self._get_ipmi_version(), []

    def _get_ipmi_version(self) -> ServiceDetails:
        if self._host_sections is None:
            return "unknown"

        section = self._host_sections.sections.get(SectionName("mgmt_ipmi_firmware"))
        if not section:
            return "unknown"

        for line in section:
            if line[0] == "BMC Version" and line[1] == "version":
                return line[2]

        return "unknown"
