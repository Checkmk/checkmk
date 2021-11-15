#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Dict, NamedTuple

from .agent_based_api.v1 import exists, register, Result, Service, SNMPTree, State, TableRow
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, InventoryResult, StringTable


class WLCAp(NamedTuple):
    status: str
    unprovisioned: str
    ip_addr: str
    group: str
    model: str
    serial: str
    sys_location: str


Section = Dict[str, WLCAp]

_MAP_AP_PRODUCTS = {
    "1": "a50",
    "2": "a52",
    "3": "a60",
    "4": "a61",
    "5": "a70",
    "6": "walljackAp61",
    "7": "a2E",
    "8": "ap1200",
    "9": "ap80s",
    "10": "ap80m",
    "11": "wg102",
    "12": "ap40",
    "13": "ap41",
    "14": "ap65",
    "15": "NesotMW1700",
    "16": "ortronics Wi Jack Duo",
    "17": "ortronics Duo",
    "18": "ap80MB",
    "19": "ap80SB",
    "20": "ap85",
    "21": "ap124",
    "22": "ap125",
    "23": "ap120",
    "24": "ap121",
    "25": "ap1250",
    "26": "ap120abg",
    "27": "ap121abg",
    "28": "ap124abg",
    "29": "ap125abg",
    "30": "rap5wn",
    "31": "rap5",
    "32": "rap2wg",
    "33": "reserved-4",
    "34": "ap105",
    "35": "ap65wb",
    "36": "ap651",
    "37": "reserved-6",
    "38": "ap60p",
    "39": "reserved-7",
    "40": "ap92",
    "41": "ap93",
    "42": "ap68",
    "43": "ap68p",
    "44": "ap175p",
    "45": "ap175ac",
    "46": "ap175dc",
    "47": "ap134",
    "48": "ap135",
    "49": "reserved-8",
    "50": "ap93h",
    "51": "rap3wn",
    "52": "rap3wnp",
    "53": "ap104",
    "54": "rap155",
    "55": "rap155p",
    "56": "rap108",
    "57": "rap109",
    "58": "ap224",
    "59": "ap225",
    "60": "ap114",
    "61": "ap115",
    "62": "rap109L",
    "63": "ap274",
    "64": "ap275",
    "65": "ap214a",
    "66": "ap215a",
    "67": "ap204",
    "68": "ap205",
    "69": "ap103",
    "70": "ap103H",
    "72": "ap227",
    "73": "ap214",
    "74": "ap215",
    "75": "ap228",
    "76": "ap205H",
    "9999": "undefined",
}


def parse_aruba_wlc_aps(string_table: StringTable) -> Section:
    return {
        ap_name: WLCAp(
            status=ap_status,
            unprovisioned=ap_unprovisioned,
            ip_addr=ap_ip,
            group=ap_group,
            model=_MAP_AP_PRODUCTS.get(ap_model.split(".")[-1], "unknown"),
            serial=ap_serial,
            sys_location=ap_sysloc,
        )
        for (
            ap_name,
            ap_status,
            ap_unprovisioned,
            ap_ip,
            ap_group,
            ap_model,
            ap_serial,
            ap_sysloc,
        ) in string_table
    }


register.snmp_section(
    name="aruba_wlc_aps",
    parse_function=parse_aruba_wlc_aps,
    detect=exists(".1.3.6.1.4.1.2036.2.1.1.4.0"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.14823.2.2.1.5.2.1.4.1",
        oids=[
            "3",  # wlanAPName
            "19",  # wlanAPStatus
            "22",  # wlanAPUnprovisioned
            "2",  # wlanAPIpAddress
            "4",  # wlanAPGroupName
            "5",  # wlanAPModel
            "6",  # wlanAPSerialNumber
            "32",  # wlanAPSysLocation
        ],
    ),
)


def discover_aruba_wlc_aps(section: Section) -> DiscoveryResult:
    for ap_name, ap_data in section.items():
        if ap_data.status == "1" and ap_data.unprovisioned != "1":
            yield Service(item=ap_name)


def check_aruba_wlc_aps(item: str, section: Section) -> CheckResult:
    if item not in section:
        return

    map_state = {
        "1": (0, "up"),
        "2": (2, "down"),
    }
    ap_data = section[item]

    state, state_readable = map_state[ap_data.status]
    infotext = "Status: %s" % state_readable
    if ap_data.group:
        infotext += ", Group: %s" % ap_data.group
    if ap_data.sys_location:
        infotext += ", System location: %s" % ap_data.sys_location
    yield Result(
        state=State(state),
        summary=infotext,
    )

    if ap_data.unprovisioned == "1":
        yield Result(
            state=State.WARN,
            summary="Unprovisioned: yes",
        )


register.check_plugin(
    name="aruba_wlc_aps",
    service_name="AP %s",
    discovery_function=discover_aruba_wlc_aps,
    check_function=check_aruba_wlc_aps,
)


def inventory_aruba_wlc_aps(section: Section) -> InventoryResult:
    path = ["networking", "wlan", "controller", "accesspoints"]
    for ap_name, ap_data in section.items():
        yield TableRow(
            path=path,
            key_columns={"name": ap_name},
            inventory_columns={
                "ip_addr": ap_data.ip_addr,
                "group": ap_data.group,
                "model": ap_data.model,
                "serial": ap_data.serial,
                "sys_location": ap_data.sys_location,
            },
        )


register.inventory_plugin(
    name="aruba_wlc_aps",
    inventory_function=inventory_aruba_wlc_aps,
)
