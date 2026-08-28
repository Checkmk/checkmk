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
from cmk.plugins.hitachi_hnas.lib import DETECT

_STATUS_MAP = (
    "unknown",
    "unconfigured",
    "offLine",
    "owned",
    "configured",
    "granted",
    "clusterNodeNotUp",
    "misconfigured",
)


def parse_hitachi_hnas_quorumdevice(string_table: StringTable) -> StringTable | None:
    return string_table or None


def discover_hitachi_hnas_quorumdevice(section: StringTable) -> DiscoveryResult:
    yield Service()


def check_hitachi_hnas_quorumdevice(section: StringTable) -> CheckResult:
    status = int(section[0][0])
    if status >= len(_STATUS_MAP):
        yield Result(
            state=State.UNKNOWN, summary=f"Quorum Device reports unidentified status {status}"
        )
        return

    yield Result(
        state=State.OK if status == 4 else State.WARN,
        summary=f"Quorum Device reports status {_STATUS_MAP[status]}",
    )


snmp_section_hitachi_hnas_quorumdevice = SimpleSNMPSection(
    name="hitachi_hnas_quorumdevice",
    parse_function=parse_hitachi_hnas_quorumdevice,
    detect=DETECT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.11096.6.1.1.1.2.5",
        oids=["7"],
    ),
)


check_plugin_hitachi_hnas_quorumdevice = CheckPlugin(
    name="hitachi_hnas_quorumdevice",
    service_name="Quorum Device",
    discovery_function=discover_hitachi_hnas_quorumdevice,
    check_function=check_hitachi_hnas_quorumdevice,
)
