#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping
from typing import TypedDict

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Metric,
    render,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.emc.lib import DETECT_DATADOMAIN


class MTreeData(TypedDict):
    precompiled: int
    status_code: str


type Section = Mapping[str, MTreeData]


def parse_emc_datadomain_mtree(string_table: StringTable) -> Section:
    return {
        line[0]: MTreeData(precompiled=int(float(line[1]) * 1024**3), status_code=line[2])
        for line in string_table
    }


def check_emc_datadomain_mtree(
    item: str, params: Mapping[str, int], section: Section
) -> CheckResult:
    if not (mtree_data := section.get(item)):
        return
    state_table = {
        "0": "unknown",
        "1": "deleted",
        "2": "read-only",
        "3": "read-write",
        "4": "replication destination",
        "5": "retention lock enabled",
        "6": "retention lock disabled",
    }
    dev_state_str = state_table.get(
        mtree_data["status_code"], f"invalid code {mtree_data['status_code']}"
    )
    state_int = params.get(dev_state_str, 3)
    state = State(state_int) if state_int in (0, 1, 2, 3) else State.UNKNOWN
    yield Result(
        state=state,
        summary=f"Status: {dev_state_str}, Precompiled: {render.bytes(mtree_data['precompiled'])}",
    )
    yield Metric("precompiled", mtree_data["precompiled"])


def discover_emc_datadomain_mtree(section: Section) -> DiscoveryResult:
    yield from (Service(item=item) for item in section)


snmp_section_emc_datadomain_mtree = SimpleSNMPSection(
    name="emc_datadomain_mtree",
    detect=DETECT_DATADOMAIN,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.19746.1.15.2.1.1",
        oids=["2", "3", "4"],
    ),
    parse_function=parse_emc_datadomain_mtree,
)


check_plugin_emc_datadomain_mtree = CheckPlugin(
    name="emc_datadomain_mtree",
    service_name="MTree %s",
    discovery_function=discover_emc_datadomain_mtree,
    check_function=check_emc_datadomain_mtree,
    check_ruleset_name="emc_datadomain_mtree",
    check_default_parameters={
        "deleted": 2,
        "read-only": 1,
        "read-write": 0,
        "replication destination": 0,
        "retention lock disabled": 0,
        "retention lock enabled": 0,
        "unknown": 3,
    },
)
