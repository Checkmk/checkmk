#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import AgentSection, CheckPlugin, CheckResult, DiscoveryResult
from cmk.plugins.windows.agent_based.libwmi import (
    check_wmi_raw_persec,
    discover_wmi_table_total,
    parse_wmi_table,
    WMISection,
)


def discover_msexch_availability(section: WMISection) -> DiscoveryResult:
    yield from discover_wmi_table_total(section)


def check_msexch_availability(section: WMISection) -> CheckResult:
    yield from check_wmi_raw_persec(
        section[""],
        "",
        "AvailabilityRequestssec",
        metric_name="requests_per_sec",
        label="Requests/sec",
    )


agent_section_msexch_availability = AgentSection(
    name="msexch_availability",
    parse_function=parse_wmi_table,
)


check_plugin_msexch_availability = CheckPlugin(
    name="msexch_availability",
    service_name="Exchange Availability Service",
    discovery_function=discover_msexch_availability,
    check_function=check_msexch_availability,
)
