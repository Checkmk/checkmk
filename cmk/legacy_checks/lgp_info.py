#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Check has been developed using a Emerson Network Power Rack PDU Card
# Agent App Firmware Version  4.840.0
# Agent Boot Firmware Version 4.540.3
# FDM Version 1209
# GDD Version 45585

# Example info data:
# [[['Rack PDU Card', '4.840.0', '535055G103T2010JUN240295']], [['1', '1', '.1.3.6.1.4.1.476.1.42.4.8.2.2', 'Emerson Network Power', '1']]]


from collections.abc import Sequence

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    SNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.lgp.lib import DETECT_LGP

_LGP_INFO_DEVICES = {
    ".1.3.6.1.4.1.476.1.42.4.8.2.1": "lgpMPX",
    ".1.3.6.1.4.1.476.1.42.4.8.2.2": "lgpMPH",
}


def discover_lgp_info(section: Sequence[StringTable]) -> DiscoveryResult:
    if section and section[0] and section[0][0]:
        yield Service()


def check_lgp_info(section: Sequence[StringTable]) -> CheckResult:
    if not (section and section[0] and section[0][0]):
        return

    model, firmware, serial = section[0][0]
    summary = f"Model: {model}, Firmware: {firmware}, S/N: {serial}"

    if len(section) > 1:
        devices = "\n".join(
            f"ID: {_LGP_INFO_DEVICES.get(id_, id_)}, Manufacturer: {manufacturer}, Unit-Number: {unit_number}"
            for id_, manufacturer, unit_number in section[1]
        )
        yield Result(state=State.OK, summary=summary, details=devices)
    else:
        yield Result(state=State.OK, summary=summary)


def parse_lgp_info(string_table: Sequence[StringTable]) -> Sequence[StringTable]:
    return string_table


snmp_section_lgp_info = SNMPSection(
    name="lgp_info",
    detect=DETECT_LGP,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.476.1.42.2.1",
            oids=["2.0", "3.0", "4.0"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.476.1.42.2.4.2.1",
            oids=["2", "3", "6"],
        ),
    ],
    parse_function=parse_lgp_info,
)


check_plugin_lgp_info = CheckPlugin(
    name="lgp_info",
    service_name="Liebert Info",
    discovery_function=discover_lgp_info,
    check_function=check_lgp_info,
)
