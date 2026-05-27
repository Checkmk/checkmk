#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# MIB structure:
# 1.3.6.1.4.1.52.4.3.1.2.1.1.1    ctChasPowerSupplyNum
# 1.3.6.1.4.1.52.4.3.1.2.1.1.2    ctChasPowerSupplyState
# 1.3.6.1.4.1.52.4.3.1.2.1.1.3    ctChasPowerSupplyType
# 1.3.6.1.4.1.52.4.3.1.2.1.1.4    ctChasPowerSupplyRedundancy


from collections.abc import Mapping, Sequence

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    OIDEnd,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.enterasys.lib import DETECT_ENTERASYS

_SUPPLY_TYPES = {
    "1": "ac-dc",
    "2": "dc-dc",
    "3": "notSupported",
    "4": "highOutput",
}
_REDUNDANCY_TYPES = {
    "1": "redundant",
    "2": "notRedundant",
    "3": "notSupported",
}


def parse_enterasys_powersupply(string_table: StringTable) -> StringTable:
    return string_table


def discover_enterasys_powersupply(section: StringTable) -> DiscoveryResult:
    for num, state, _typ, _redun in section:
        if state == "3":
            yield Service(item=num)


def check_enterasys_powersupply(
    item: str, params: Mapping[str, Sequence[int]], section: StringTable
) -> CheckResult:
    for num, state, typ, redun in section:
        if num != item:
            continue
        if state == "4":
            yield Result(state=State.CRIT, summary="Status: installed and not operating")
            return

        redun_mapped = _REDUNDANCY_TYPES.get(redun, f"unknown[{redun}]")
        if redun and int(redun) in params["redundancy_ok_states"]:
            supply_type = _SUPPLY_TYPES.get(typ, f"unknown[{typ}]")
            yield Result(
                state=State.OK,
                summary=f"Status: working and {redun_mapped} ({supply_type})",
            )
            return
        yield Result(state=State.WARN, summary=f"Status: {redun_mapped}")
        return


snmp_section_enterasys_powersupply = SimpleSNMPSection(
    name="enterasys_powersupply",
    detect=DETECT_ENTERASYS,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.52.4.3.1.2.1.1",
        oids=[OIDEnd(), "2", "3", "4"],
    ),
    parse_function=parse_enterasys_powersupply,
)


check_plugin_enterasys_powersupply = CheckPlugin(
    name="enterasys_powersupply",
    service_name="PSU %s",
    discovery_function=discover_enterasys_powersupply,
    check_function=check_enterasys_powersupply,
    check_ruleset_name="enterasys_powersupply",
    check_default_parameters={
        "redundancy_ok_states": [
            1,
        ],
    },
)
