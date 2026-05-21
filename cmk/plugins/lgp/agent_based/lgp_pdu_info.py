#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


# Check has been developed using a Emerson Network Power Rack PDU Card
# Agent App Firmware Version  4.840.0
# Agent Boot Firmware Version 4.540.3
# FDM Version 1209
# GDD Version 45585

# Example info:
# [['1', 'TEST-123-HOST', '1', '535055G103T2010JUN240295', '1']]


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
from cmk.plugins.lgp.lib import DETECT_LGP


def discover_lgp_pdu_info(section: StringTable) -> DiscoveryResult:
    for pdu in section:
        # Use the SysAssignLabel as item
        yield Service(item=pdu[2])


def check_lgp_pdu_info(item: str, section: StringTable) -> CheckResult:
    for pdu in section:
        if pdu[2] == item:
            entry_id, label, sys_label, serial, num_rcs = pdu
            yield Result(
                state=State.OK,
                summary=f"Entry-ID: {entry_id}, Label: {label} ({sys_label}), S/N: {serial}, Num. RCs: {num_rcs}",
            )
            return

    yield Result(state=State.UNKNOWN, summary="Device can not be found in SNMP output.")


def parse_lgp_pdu_info(string_table: StringTable) -> StringTable:
    return string_table


snmp_section_lgp_pdu_info = SimpleSNMPSection(
    name="lgp_pdu_info",
    detect=DETECT_LGP,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.476.1.42.3.8.20.1",
        oids=["5", "10", "15", "45", "50"],
    ),
    parse_function=parse_lgp_pdu_info,
)


check_plugin_lgp_pdu_info = CheckPlugin(
    name="lgp_pdu_info",
    service_name="Liebert PDU Info %s",
    discovery_function=discover_lgp_pdu_info,
    check_function=check_lgp_pdu_info,
)
