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
    ("", State.UNKNOWN),
    ("unknown", State.UNKNOWN),
    ("up", State.OK),
    ("notUp", State.WARN),
    ("onLine", State.OK),
    ("dead", State.CRIT),
    ("dormant", State.CRIT),
)


def _combine_item(id_: str, name: str) -> str:
    return f"{id_} {name}" if name else id_


def parse_hitachi_hnas_pnode(string_table: StringTable) -> StringTable:
    return string_table


def discover_hitachi_hnas_pnode(section: StringTable) -> DiscoveryResult:
    for id_, name, _status in section:
        yield Service(item=_combine_item(id_, name))


def check_hitachi_hnas_pnode(item: str, section: StringTable) -> CheckResult:
    for id_, name, raw_status in section:
        if _combine_item(id_, name) != item:
            continue

        status = int(raw_status)
        if status == 0 or status >= len(_STATUS_MAP):
            yield Result(state=State.UNKNOWN, summary=f"PNode reports unidentified status {status}")
            return

        name_, state = _STATUS_MAP[status]
        yield Result(state=state, summary=f"PNode reports status {name_}")
        return

    yield Result(state=State.UNKNOWN, summary="SNMP did not report a status of this PNode")


snmp_section_hitachi_hnas_pnode = SimpleSNMPSection(
    name="hitachi_hnas_pnode",
    parse_function=parse_hitachi_hnas_pnode,
    detect=DETECT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.11096.6.1.1.1.2.5.9.1",
        oids=["1", "2", "4"],
    ),
)


check_plugin_hitachi_hnas_pnode = CheckPlugin(
    name="hitachi_hnas_pnode",
    service_name="PNode %s",
    discovery_function=discover_hitachi_hnas_pnode,
    check_function=check_hitachi_hnas_pnode,
)
