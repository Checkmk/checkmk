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
    ("", State.UNKNOWN),  # 0
    ("ok", State.OK),  # 1
    ("failed", State.CRIT),  # 2
    ("notFitted", State.WARN),  # 3
    ("unknown", State.UNKNOWN),  # 4
)


def parse_hitachi_hnas_psu(string_table: StringTable) -> StringTable:
    return string_table


def discover_hitachi_hnas_psu(section: StringTable) -> DiscoveryResult:
    for clusternode, id_, _status in section:
        yield Service(item=f"{clusternode}.{id_}")


def check_hitachi_hnas_psu(item: str, section: StringTable) -> CheckResult:
    for clusternode, id_, status_str in section:
        if f"{clusternode}.{id_}" != item:
            continue

        status_int = int(status_str)
        if status_int == 0 or status_int >= len(_STATUS_MAP):
            yield Result(
                state=State.UNKNOWN,
                summary=f"PNode {clusternode} PSU {id_} reports unidentified status {status_int}",
            )
            return

        name, state = _STATUS_MAP[status_int]
        yield Result(state=state, summary=f"PNode {clusternode} PSU {id_} reports status {name}")
        return

    yield Result(state=State.UNKNOWN, summary="SNMP did not report a status of this PSU")


snmp_section_hitachi_hnas_psu = SimpleSNMPSection(
    name="hitachi_hnas_psu",
    parse_function=parse_hitachi_hnas_psu,
    detect=DETECT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.11096.6.1.1.1.2.1.13.1",
        oids=["1", "2", "3"],
    ),
)


check_plugin_hitachi_hnas_psu = CheckPlugin(
    name="hitachi_hnas_psu",
    service_name="PSU %s",
    discovery_function=discover_hitachi_hnas_psu,
    check_function=check_hitachi_hnas_psu,
)
