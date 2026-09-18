#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    render,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.mcafee.libgateway import DETECT_EMAIL_GATEWAY


def parse_mcafee_emailgateway_smtp(string_table: StringTable) -> StringTable | None:
    return string_table or None


def discover_mcafee_emailgateway_smtp(section: StringTable) -> DiscoveryResult:  # noqa: ARG001
    yield Service()


def check_mcafee_emailgateway_smtp(section: StringTable) -> CheckResult:
    total_connections, total_bytes, kernel_mode_blocked, kernel_mode_active = map(int, section[0])
    yield Result(
        state=State.OK,
        summary=(
            f"Total connections: {total_connections} ({render.bytes(total_bytes)}), "
            f"Kernel blocked: {kernel_mode_blocked}, Kernel active: {kernel_mode_active}"
        ),
    )


snmp_section_mcafee_emailgateway_smtp = SimpleSNMPSection(
    name="mcafee_emailgateway_smtp",
    detect=DETECT_EMAIL_GATEWAY,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.1230.2.4.1.2.3.3",
        oids=["1", "2", "3", "4"],
    ),
    parse_function=parse_mcafee_emailgateway_smtp,
)


check_plugin_mcafee_emailgateway_smtp = CheckPlugin(
    name="mcafee_emailgateway_smtp",
    service_name="SMTP",
    discovery_function=discover_mcafee_emailgateway_smtp,
    check_function=check_mcafee_emailgateway_smtp,
)
