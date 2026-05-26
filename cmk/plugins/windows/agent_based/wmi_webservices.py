#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
)
from cmk.plugins.windows.agent_based.libwmi import (
    check_wmi_raw_counter,
    discover_wmi_table_instances,
    parse_wmi_table,
    WMISection,
)


def discover_wmi_webservices(section: WMISection) -> DiscoveryResult:
    yield from discover_wmi_table_instances(section)


def check_wmi_webservices(item: str, section: WMISection) -> CheckResult:
    yield from check_wmi_raw_counter(
        section[""],
        item,
        "CurrentConnections",
        metric_name="connections",
        label="Connections",
        render_func=lambda v: str(int(v)),
    )


agent_section_wmi_webservices = AgentSection(
    name="wmi_webservices",
    parse_function=parse_wmi_table,
)


check_plugin_wmi_webservices = CheckPlugin(
    name="wmi_webservices",
    service_name="Web Service %s",
    discovery_function=discover_wmi_webservices,
    check_function=check_wmi_webservices,
)
