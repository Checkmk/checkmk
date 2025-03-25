#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

from cmk.agent_based.v1 import check_levels as check_levels_v1
from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    StringTable,
)
from cmk.agent_based.v2.render import percent
from cmk.plugins.lib.fortinet import DETECT_FORTIMAIL

Section = Mapping[str, float]


def parse_fortimail_disk_usage(string_table: StringTable) -> Section | None:
    """
    >>> parse_fortimail_disk_usage([["13"]])
    {'disk_usage': 13.0}
    """
    return {"disk_usage": float(string_table[0][0])} if string_table else None


def discover_fortimail_disk_usage(section: Section) -> DiscoveryResult:
    yield Service()


def check_fortimail_disk_usage(
    params: Mapping[str, tuple[float, float] | None],
    section: Section,
) -> CheckResult:
    yield from check_levels_v1(
        section["disk_usage"],
        levels_upper=params["disk_usage"],
        metric_name="disk_utilization",
        label="Disk usage",
        render_func=percent,
    )


snmp_section_fortimail_disk_usage = SimpleSNMPSection(
    name="fortimail_disk_usage",
    parse_function=parse_fortimail_disk_usage,
    detect=DETECT_FORTIMAIL,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.12356.105.1",
        oids=[
            "9",  # fmlSysMailDiskUsage
        ],
    ),
)

check_plugin_fortimail_disk_usage = CheckPlugin(
    name="fortimail_disk_usage",
    service_name="Disk usage",
    discovery_function=discover_fortimail_disk_usage,
    check_function=check_fortimail_disk_usage,
    check_default_parameters={"disk_usage": (80.0, 90.0)},
    check_ruleset_name="fortimail_disk_usage",
)
