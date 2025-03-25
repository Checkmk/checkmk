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
from cmk.plugins.lib.datapower import DETECT


def inventory_datapower_pdrive(section: StringTable) -> DiscoveryResult:
    for (
        controller,
        device,
        _ldrive,
        _position,
        status,
        _progress,
        _vendor,
        _product,
        _fail,
    ) in section:
        if status != "12":
            item = f"{controller}-{device}"
            yield Service(item=item)


def check_datapower_pdrive(item: str, section: StringTable) -> CheckResult:
    datapower_pdrive_status = {
        "1": (State.OK, "Unconfigured/Good"),
        "2": (State.OK, "Unconfigured/Good/Foreign"),
        "3": (State.WARN, "Unconfigured/Bad"),
        "4": (State.WARN, "Unconfigured/Bad/Foreign"),
        "5": (State.OK, "Hot spare"),
        "6": (State.WARN, "Offline"),
        "7": (State.CRIT, "Failed"),
        "8": (State.WARN, "Rebuilding"),
        "9": (State.OK, "Online"),
        "10": (State.WARN, "Copyback"),
        "11": (State.WARN, "System"),
        "12": (State.WARN, "Undefined"),
    }
    datapower_pdrive_fail = {
        "1": Result(state=State.CRIT, summary="disk reports failure"),
        "2": Result(state=State.OK, summary="disk reports no failure"),
    }
    datapower_pdrive_position = {
        "1": "HDD 0",
        "2": "HDD 1",
        "3": "HDD 2",
        "4": "HDD 3",
        "5": "undefined",
    }
    for controller, device, ldrive, position, status, progress, vendor, product, fail in section:
        if item == f"{controller}-{device}":
            member_of_ldrive = f"{controller}-{ldrive}"
            state, state_txt = datapower_pdrive_status[status]
            position_txt = datapower_pdrive_position[position]
            if int(progress) != 0:
                progress_txt = " - Progress: %s%%" % progress
            else:
                progress_txt = ""
            infotext = f"{state_txt}{progress_txt}, Position: {position_txt}, Logical Drive: {member_of_ldrive}, Product: {vendor} {product}"
            yield Result(state=state, summary=infotext)

            if fail:
                yield datapower_pdrive_fail[fail]


def parse_datapower_pdrive(string_table: StringTable) -> StringTable:
    return string_table


snmp_section_datapower_pdrive = SimpleSNMPSection(
    name="datapower_pdrive",
    detect=DETECT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.14685.3.1.260.1",
        oids=["1", "2", "4", "6", "7", "8", "14", "15", "18"],
    ),
    parse_function=parse_datapower_pdrive,
)
check_plugin_datapower_pdrive = CheckPlugin(
    name="datapower_pdrive",
    service_name="Physical Drive %s",
    discovery_function=inventory_datapower_pdrive,
    check_function=check_datapower_pdrive,
)
