#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"

# Older versions replay an empty string if the state is Unknown / Error state


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
from cmk.plugins.stormshield.lib import DETECT_STORMSHIELD_CLUSTER

sync_name_mapping = {
    "1": "Synced",
    "0": "Not Synced",
    "-1": "Unknown / Error",
    "": "Unknown / Error",
}

sync_status_mapping = {
    "1": State.OK,
    "0": State.CRIT,
    "-1": State.UNKNOWN,
    "": State.UNKNOWN,
}


def discover_stormshield_cluster(section: StringTable) -> DiscoveryResult:
    yield Service()


def check_stormshield_cluster(section: StringTable) -> CheckResult:
    for number, not_replying, active, eth_links, faulty_links, sync in section:
        _not_replying = int(not_replying)
        _faulty_links = int(faulty_links)

        yield Result(
            state=sync_status_mapping[sync], summary="Sync Status: %s" % sync_name_mapping[sync]
        )
        yield Result(
            state=State.OK, summary=f"Member: {number}, Active: {active}, Links used: {eth_links}"
        )

        if _not_replying > 0:
            status = State.CRIT
        else:
            status = State.OK
        yield Result(state=status, summary="Not replying: %s" % _not_replying)

        if _faulty_links > 0:
            status = State.CRIT
        else:
            status = State.OK
        yield Result(state=status, summary="Faulty: %s" % _faulty_links)


def parse_stormshield_cluster(string_table: StringTable) -> StringTable | None:
    return string_table or None


snmp_section_stormshield_cluster = SimpleSNMPSection(
    name="stormshield_cluster",
    detect=DETECT_STORMSHIELD_CLUSTER,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.11256.1.11",
        oids=["1", "2", "3", "5", "6", "8"],
    ),
    parse_function=parse_stormshield_cluster,
)


check_plugin_stormshield_cluster = CheckPlugin(
    name="stormshield_cluster",
    service_name="HA Status",
    discovery_function=discover_stormshield_cluster,
    check_function=check_stormshield_cluster,
)
