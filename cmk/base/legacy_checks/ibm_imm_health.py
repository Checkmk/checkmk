#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.plugins.ibm.lib import DETECT_IBM_IMM

check_info = {}


def discover_ibm_imm_health(info):
    if info:
        return [(None, None)]
    return []


def check_ibm_imm_health(_no_item, _no_params, info):
    if not info or not info[0]:
        return 3, "Health info not found in SNMP data"

    num_alerts = int((len(info) - 1) / 3)
    infotext = ""
    for i in range(0, num_alerts):
        state = info[num_alerts + 1 + i][0]
        text = info[num_alerts * 2 + 1 + i][0]
        if infotext != "":
            infotext += ", "
        infotext += f"{text}({state})"

    state = info[0][0]
    if state == "255":
        return (0, "no problem found")
    if state == "0":
        return (2, infotext + " - manual log clearing needed to recover state")
    if state == "2":
        return (2, infotext)
    if state == "4":
        return (1, infotext)
    return (3, infotext)


def parse_ibm_imm_health(string_table: StringTable) -> StringTable:
    return string_table


check_info["ibm_imm_health"] = LegacyCheckDefinition(
    name="ibm_imm_health",
    parse_function=parse_ibm_imm_health,
    detect=DETECT_IBM_IMM,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.2.3.51.3.1",
        oids=["4"],
    ),
    service_name="System health",
    discovery_function=discover_ibm_imm_health,
    check_function=check_ibm_imm_health,
)
