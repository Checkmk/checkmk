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
    startswith,
    State,
    StringTable,
)

_STATUS_VALUES = {
    0: (State.OK, "Array in normal status"),
    1: (State.CRIT, "Drive blocked"),
    2: (State.CRIT, "Spare drive blockade"),
    4: (State.CRIT, "Data drive blockade"),
    8: (State.WARN, "ENC alarm"),
    64: (State.WARN, "Warned array"),
    128: (State.CRIT, "Mate controller blocked"),
    256: (State.CRIT, "UPS alarm"),
    1024: (State.CRIT, "Path blocked"),
    16384: (State.CRIT, "Drive I/O module failure"),
    32768: (State.CRIT, "Controller failure by related parts"),
    65536: (State.WARN, "Battery alarm"),
    131072: (State.CRIT, "Power supply failure"),
    1048576: (State.WARN, "Fan alarm"),
    4194304: (State.CRIT, "Host I/O module failure"),
    8388608: (State.CRIT, "Management module failure"),
    16777216: (State.CRIT, "Host connector alarm"),
    268435456: (State.CRIT, "Host connector alarm"),
}


def parse_hitachi_hus_status(string_table: StringTable) -> StringTable | None:
    return string_table or None


def discover_hitachi_hus_status(section: StringTable) -> DiscoveryResult:
    yield Service()


def check_hitachi_hus_status(section: StringTable) -> CheckResult:
    raw_error_code = section[0][0]
    error_code = int(raw_error_code)
    if error_code == 0:
        yield Result(state=State.OK, summary="Array in normal status")
        return

    yield Result(state=State.OK, summary=f"Errorcode: {raw_error_code}")
    for status, (state, message) in _STATUS_VALUES.items():
        if status & error_code:
            yield Result(state=state, summary=message)


snmp_section_hitachi_hus_status = SimpleSNMPSection(
    name="hitachi_hus_status",
    parse_function=parse_hitachi_hus_status,
    detect=startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.116"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.116.5.11.1.2.2",
        oids=["1"],
    ),
)


check_plugin_hitachi_hus_status = CheckPlugin(
    name="hitachi_hus_status",
    service_name="Status",
    discovery_function=discover_hitachi_hus_status,
    check_function=check_hitachi_hus_status,
)
