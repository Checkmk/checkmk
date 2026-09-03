#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

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
from cmk.plugins.mcafee.libgateway import DETECT_EMAIL_GATEWAY


def parse_mcafee_emailgateway_agent(string_table: StringTable) -> StringTable | None:
    return string_table or None


def discover_mcafee_emailgateway_agent(section: StringTable) -> DiscoveryResult:
    yield Service()


def check_mcafee_emailgateway_agent(section: StringTable) -> CheckResult:
    version, hostname, last_update = section[0]
    yield Result(
        state=State.OK,
        summary=f"Version: {version}, Hostname: {hostname}, Last file update: {last_update}",
    )


snmp_section_mcafee_emailgateway_agent = SimpleSNMPSection(
    name="mcafee_emailgateway_agent",
    detect=DETECT_EMAIL_GATEWAY,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.1230.2.4.1.2.1.1",
        oids=["1", "2", "3"],
    ),
    parse_function=parse_mcafee_emailgateway_agent,
)


check_plugin_mcafee_emailgateway_agent = CheckPlugin(
    name="mcafee_emailgateway_agent",
    service_name="Agent Info",
    discovery_function=discover_mcafee_emailgateway_agent,
    check_function=check_mcafee_emailgateway_agent,
)
