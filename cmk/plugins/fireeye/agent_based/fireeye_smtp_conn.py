#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Metric,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.fireeye.lib import DETECT

# .1.3.6.1.4.1.25597.13.1.46.0 8


def check_fireeye_smtp_conn(section: StringTable) -> CheckResult:
    smtp_conns = int(section[0][0])
    yield Result(state=State.OK, summary=f"Open SMTP connections: {smtp_conns}")
    yield Metric("connections", smtp_conns)


def parse_fireeye_smtp_conn(string_table: StringTable) -> StringTable:
    return string_table


def discover_fireeye_smtp_conn(section: StringTable) -> DiscoveryResult:
    if section:
        yield Service()


snmp_section_fireeye_smtp_conn = SimpleSNMPSection(
    name="fireeye_smtp_conn",
    parse_function=parse_fireeye_smtp_conn,
    detect=DETECT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.25597.13.1",
        oids=["46"],
    ),
)


check_plugin_fireeye_smtp_conn = CheckPlugin(
    name="fireeye_smtp_conn",
    service_name="SMTP Connections",
    discovery_function=discover_fireeye_smtp_conn,
    check_function=check_fireeye_smtp_conn,
)
