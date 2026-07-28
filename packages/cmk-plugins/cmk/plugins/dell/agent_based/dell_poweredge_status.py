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
from cmk.plugins.dell.lib import DETECT_IDRAC_POWEREDGE

_STATE_TABLE = {
    "1": (State.WARN, "other, "),
    "2": (State.WARN, "unknown, "),
    "3": (State.OK, ""),
    "4": (State.WARN, "nonCritical, "),
    "5": (State.CRIT, "Critical, "),
    "6": (State.CRIT, "NonRecoverable, "),
}


def discover_dell_poweredge_status(section: StringTable) -> DiscoveryResult:
    if section:
        yield Service()


def check_dell_poweredge_status(section: StringTable) -> CheckResult:
    rac_url, chassis, slot, model, status, service_tag, express_service_code = section[0]
    state, status_txt = _STATE_TABLE.get(status, (State.CRIT, "unknown state, "))
    details = {
        "racURL": rac_url,
        "Chassis": chassis,
        "Slot": slot,
        "Model": model,
        "ServiceTag": service_tag,
        "ExpressServiceCode": express_service_code,
    }
    summary = status_txt + ", ".join(f"{k}: {v}" for k, v in details.items())
    yield Result(state=state, summary=summary)


def parse_dell_poweredge_status(string_table: StringTable) -> StringTable | None:
    return string_table or None


snmp_section_dell_poweredge_status = SimpleSNMPSection(
    name="dell_poweredge_status",
    detect=DETECT_IDRAC_POWEREDGE,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.674.10892.5",
        oids=[
            "1.1.6.0",
            "1.2.2.0",
            "1.3.5.0",
            "1.3.12.0",
            "2.1.0",
            "4.300.10.1.11.1",
            "4.300.10.1.49.1",
        ],
    ),
    parse_function=parse_dell_poweredge_status,
)
check_plugin_dell_poweredge_status = CheckPlugin(
    name="dell_poweredge_status",
    service_name="PowerEdge Health",
    discovery_function=discover_dell_poweredge_status,
    check_function=check_dell_poweredge_status,
)
