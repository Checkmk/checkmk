#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Dict, List, Optional, cast

from cmk.utils.type_defs import (
    HostAddress,
    HostName,
    PluginName,
    RawAgentData,
    ServiceCheckResult,
    ServiceDetails,
    SourceType,
)

from cmk.base.config import IPMICredentials, SectionPlugin
from cmk.base.exceptions import MKAgentError

from cmk.fetchers import IPMIDataFetcher

from .abstract import CheckMKAgentDataSource


# NOTE: This class is *not* abstract, even if pylint is too dumb to see that!
class IPMIManagementBoardDataSource(CheckMKAgentDataSource):
    source_type = SourceType.MANAGEMENT

    _raw_sections = {PluginName("mgmt_ipmi_sensors")}

    def __init__(
            self,
            hostname,  # type: HostName
            ipaddress,  # type: Optional[HostAddress]
            selected_raw_sections=None,  # type: Optional[Dict[PluginName, SectionPlugin]]
    ):
        # type: (...) -> None
        super(IPMIManagementBoardDataSource, self).__init__(
            hostname,
            ipaddress,
            None if selected_raw_sections is None else self._raw_sections,
        )
        self._credentials = cast(IPMICredentials, self._host_config.management_credentials)

    def id(self):
        # type: () -> str
        return "mgmt_ipmi"

    def title(self):
        # type: () -> str
        return "Management board - IPMI"

    def describe(self):
        # type: () -> str
        items = []
        if self._ipaddress:
            items.append("Address: %s" % self._ipaddress)
        if self._credentials:
            items.append("User: %s" % self._credentials["username"])
        return "%s (%s)" % (self.title(), ", ".join(items))

    def _cpu_tracking_id(self):
        # type: () -> str
        return self.id()

    def _execute(self):
        # type: () -> RawAgentData
        if not self._credentials:
            raise MKAgentError("Missing credentials")

        if self._ipaddress is None:
            raise MKAgentError("Missing IP address")

        with IPMIDataFetcher(self._ipaddress, self._credentials["username"],
                             self._credentials["password"]) as fetcher:
            return fetcher.data()
        raise MKAgentError("Failed to read data")

    def _summary_result(self, for_checking):
        # type: (bool) -> ServiceCheckResult
        return 0, "Version: %s" % self._get_ipmi_version(), []

    def _get_ipmi_version(self):
        # type: () -> ServiceDetails
        if self._host_sections is None:
            return "unknown"

        section = self._host_sections.sections.get("mgmt_ipmi_firmware")
        if not section:
            return "unknown"

        for line in section:
            if line[0] == "BMC Version" and line[1] == "version":
                return line[2]

        return "unknown"
