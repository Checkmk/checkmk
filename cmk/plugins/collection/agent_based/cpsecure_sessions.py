#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Example for info:
# [['HTTP',  '1', '1682'],
#  ['SMTP',  '1', '216'],
#  ['POP3',  '1', '0'],
#  ['FTP',   '1', '1'],
#  ['HTTPS', '2', '0'],
#  ['IMAP',  '1', '48']]


from cmk.agent_based.v2 import (
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    equals,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)


def inventory_cpsecure_sessions(section: StringTable) -> DiscoveryResult:
    for service, enabled, _sessions in section:
        if enabled == "1":
            yield Service(item=service)


def check_cpsecure_sessions(item: str, section: StringTable) -> CheckResult:
    for service, enabled, sessions in section:
        if item == service:
            if enabled != "1":
                yield Result(state=State.WARN, summary="service not enabled")
                return
            yield from check_levels(
                int(sessions),
                levels_upper=("fixed", (2500, 5000)),
                render_func=str,
                label="Sessions",
            )
            return


def parse_cpsecure_sessions(string_table: StringTable) -> StringTable:
    return string_table


snmp_section_cpsecure_sessions = SimpleSNMPSection(
    name="cpsecure_sessions",
    detect=equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.26546.1.1.2"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.26546.3.1.2.1.1.1",
        oids=["1", "2", "3"],
    ),
    parse_function=parse_cpsecure_sessions,
)


check_plugin_cpsecure_sessions = CheckPlugin(
    name="cpsecure_sessions",
    service_name="Number of %s sessions",
    discovery_function=inventory_cpsecure_sessions,
    check_function=check_cpsecure_sessions,
)
