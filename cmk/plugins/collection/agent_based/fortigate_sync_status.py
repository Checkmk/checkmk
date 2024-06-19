#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from typing import NamedTuple

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    SNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.lib.fortinet import DETECT_FORTIGATE


class FortigateCluster(NamedTuple):
    name: str
    status: str | None


FortigateClusterSection = Sequence[FortigateCluster]


def parse_fortigate_sync_status(string_table: Sequence[StringTable]) -> FortigateClusterSection:
    if not string_table:
        return []

    return [
        FortigateCluster(
            name=name,
            status=status if status else None,
        )
        for name, status in string_table[0]
    ]


snmp_section_fortigate_sync_status = SNMPSection(
    name="fortigate_sync_status",
    parse_function=parse_fortigate_sync_status,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.12356.101.13.2.1.1",
            oids=["11", "12"],
        ),
    ],
    detect=DETECT_FORTIGATE,
)


def discover_fortigate_sync_status(section: FortigateClusterSection) -> DiscoveryResult:
    if section and len(section) > 1:
        yield Service()


def check_fortigate_sync_status(
    section: FortigateClusterSection,
) -> CheckResult:
    map_statuses = {"0": (State.CRIT, "unsynchronized"), "1": (State.OK, "synchronized")}

    if not section:
        return

    for cluster in section:
        if not cluster.status:
            yield Result(state=State.UNKNOWN, summary=f"{cluster.name}: Status not available")
            return

        state, state_summary = map_statuses.get(
            cluster.status, (State.UNKNOWN, f"Unknown status {cluster.status}")
        )
        yield Result(
            state=state,
            summary=f"{cluster.name}: {state_summary}",
        )


check_plugin_fortigate_sync_status = CheckPlugin(
    name="fortigate_sync_status",
    service_name="Sync Status",
    check_function=check_fortigate_sync_status,
    discovery_function=discover_fortigate_sync_status,
)
