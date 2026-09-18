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
from cmk.plugins.hitachi_hnas.lib import DETECT


def parse_hitachi_hnas_cifs(string_table: StringTable) -> StringTable:
    return string_table


def discover_hitachi_hnas_cifs(section: StringTable) -> DiscoveryResult:
    for evs_id, share_name, _users in section:
        yield Service(item=f"{evs_id} {share_name}")


def check_hitachi_hnas_cifs(item: str, section: StringTable) -> CheckResult:
    for evs_id, share_name, users in section:
        if f"{evs_id} {share_name}" == item:
            yield Result(state=State.OK, summary=f"{users} users")
            yield Metric("users", float(users), boundaries=(0, None))
            return

    yield Result(state=State.UNKNOWN, summary="Share not found")


snmp_section_hitachi_hnas_cifs = SimpleSNMPSection(
    name="hitachi_hnas_cifs",
    parse_function=parse_hitachi_hnas_cifs,
    detect=DETECT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.11096.6.1.1.3.2.1.3.1",
        oids=["1", "2", "5"],
    ),
)


check_plugin_hitachi_hnas_cifs = CheckPlugin(
    name="hitachi_hnas_cifs",
    service_name="CIFS Share EVS %s",
    discovery_function=discover_hitachi_hnas_cifs,
    check_function=check_hitachi_hnas_cifs,
)
