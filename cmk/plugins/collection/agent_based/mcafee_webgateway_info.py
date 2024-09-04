#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""
The McAfee Web Gateway has been rebranded to Skyhigh Secure Web Gateway with its release 12.2.2.
Where possibile the "McAfee" string has been removed in favor of more generic therms.
The old plug-in names, value_store dict keys, and ruleset names have been kept for compatibility/history-keeping reasons.
"""

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.lib import mcafee_gateway


def parse_webgateway_info(string_table: StringTable) -> StringTable:
    return string_table


snmp_section_mcafee_webgateway_info = SimpleSNMPSection(
    name="mcafee_webgateway_info",
    parsed_section_name="webgateway_info",
    detect=mcafee_gateway.DETECT_MCAFEE_WEBGATEWAY,
    parse_function=parse_webgateway_info,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.1230.2.7.1",
        oids=["3", "9"],
    ),
)

snmp_section_skyhigh_security_webgateway_info = SimpleSNMPSection(
    name="skyhigh_security_webgateway_info",
    parsed_section_name="webgateway_info",
    detect=mcafee_gateway.DETECT_SKYHIGH_WEBGATEWAY,
    parse_function=parse_webgateway_info,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.59732.2.7.1",
        oids=["3", "9"],
    ),
)


def discovery_webgateway_info(section: StringTable) -> DiscoveryResult:
    if section:
        yield Service()


def check_webgateway_info(section: StringTable) -> CheckResult:
    version, revision = section[0]
    yield Result(state=State.OK, summary=f"Product version: {version}, Revision: {revision}")


check_plugin_mcafee_webgateway_info = CheckPlugin(
    name="mcafee_webgateway_info",
    sections=["webgateway_info"],
    discovery_function=discovery_webgateway_info,
    check_function=check_webgateway_info,
    service_name="Web gateway info",
)
