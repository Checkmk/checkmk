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


def discover_msexch_activesync(section: WMISection) -> DiscoveryResult:
    yield from discover_wmi_table_total(section)


def check_msexch_activesync(section: WMISection) -> CheckResult:
    yield from check_wmi_raw_persec(
        section[""],
        "",
        "RequestsPersec",
        metric_name="requests_per_sec",
        label="Requests/sec",
    )


agent_section_msexch_activesync = AgentSection(
    name="msexch_activesync",
    parse_function=parse_wmi_table,
)


check_plugin_msexch_activesync = CheckPlugin(
    name="msexch_activesync",
    service_name="Exchange ActiveSync",
    discovery_function=discover_msexch_activesync,
    check_function=check_msexch_activesync,
)
