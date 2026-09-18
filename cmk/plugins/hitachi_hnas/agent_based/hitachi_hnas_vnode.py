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
    ("onLine", State.OK),
    ("offLine", State.CRIT),
)


def _combine_item(id_: str, name: str) -> str:
    return f"{id_} {name}" if name else id_


def parse_hitachi_hnas_vnode(string_table: StringTable) -> StringTable:
    return string_table


def discover_hitachi_hnas_vnode(section: StringTable) -> DiscoveryResult:
    for id_, name, _status, _is_admin, _hosted_by in section:
        yield Service(item=_combine_item(id_, name))


def check_hitachi_hnas_vnode(item: str, section: StringTable) -> CheckResult:
    for id_, name, raw_status, is_admin, hosted_by in section:
        if _combine_item(id_, name) != item:
            continue

        status = int(raw_status)
        if status == 0 or status >= len(_STATUS_MAP):
            yield Result(state=State.UNKNOWN, summary=f"EVS reports unidentified status {status}")
            return

        nodetype = ""
        if is_admin == "0":
            nodetype = "This is a service node."
        if is_admin == "1":
            nodetype = "This is a administrative node."

        status_name, state = _STATUS_MAP[status]
        yield Result(
            state=state,
            summary=(
                f"EVS is hosted by PNode {hosted_by} and reports status {status_name}. {nodetype}"
            ),
        )
        return

    yield Result(state=State.UNKNOWN, summary="SNMP did not report a status of this EVS")


snmp_section_hitachi_hnas_vnode = SimpleSNMPSection(
    name="hitachi_hnas_vnode",
    parse_function=parse_hitachi_hnas_vnode,
    detect=DETECT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.11096.6.1.1.1.2.5.11.1",
        oids=["1", "2", "4", "5", "6"],
    ),
)


check_plugin_hitachi_hnas_vnode = CheckPlugin(
    name="hitachi_hnas_vnode",
    service_name="EVS %s",
    discovery_function=discover_hitachi_hnas_vnode,
    check_function=check_hitachi_hnas_vnode,
)
