#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# .1.3.6.1.4.1.318.1.1.12.1.1.0  "sf9pdu1" --> PowerNet-MIB::rPDUIdentName.0
# .1.3.6.1.4.1.318.1.1.12.1.9.0 1 --> PowerNet-MIB::rPDUIdentDeviceNumPhases.0
# .1.3.6.1.4.1.318.1.1.12.1.16.0 0 --> PowerNet-MIB::rPDUIdentDevicePowerWatts.0
# .1.3.6.1.4.1.318.1.1.12.2.3.1.1.2.1 160 --> PowerNet-MIB::rPDULoadStatusLoad.1 (measured in tenths of Amps)
# .1.3.6.1.4.1.318.1.1.12.2.3.1.1.3.1 1 --> PowerNet-MIB::rPDULoadStatusLoadState.1

# .1.3.6.1.4.1.318.1.1.12.1.1.0 FOOBAR --> PowerNet-MIB::rPDUIdentName.0
# .1.3.6.1.4.1.318.1.1.12.1.9.0 1 --> PowerNet-MIB::rPDUIdentDeviceNumPhases.0$
# .1.3.6.1.4.1.318.1.1.12.1.16.0 1587 --> PowerNet-MIB::rPDUIdentDevicePowerWatts.0
# .1.3.6.1.4.1.318.1.1.12.2.1.4.0 2 --> PowerNet-MIB::rPDULoadDevNumBanks.0
# .1.3.6.1.4.1.318.1.1.12.2.3.1.1.2.1 0 --> PowerNet-MIB::rPDULoadStatusLoad.1
# .1.3.6.1.4.1.318.1.1.12.2.3.1.1.2.2 0 --> PowerNet-MIB::rPDULoadStatusLoad.2
# .1.3.6.1.4.1.318.1.1.12.2.3.1.1.2.3 0 --> PowerNet-MIB::rPDULoadStatusLoad.3
# .1.3.6.1.4.1.318.1.1.12.2.3.1.1.3.1 1 --> PowerNet-MIB::rPDULoadStatusLoadStates.1
# .1.3.6.1.4.1.318.1.1.12.2.3.1.1.3.2 1 --> PowerNet-MIB::rPDULoadStatusLoadStates.2
# .1.3.6.1.4.1.318.1.1.12.2.3.1.1.3.3 1 --> PowerNet-MIB::rPDULoadStatusLoadStates.3

# examples num phase/banks: 1/0,    => parsed = device phase
#                           1/2,    => parsed = device phase + 2 banks
#                           3/0     => parsed = device phase + 3 phases

from typing import Dict, Tuple, Union
from cmk.snmplib.type_defs import OIDEnd, SNMPTree
from .agent_based_api.v0 import (
    all_of,
    exists,
    register,
    startswith,
)


def parse_apc_rackpdu_power(string_table):
    def get_status_info(amperage_str, device_state):
        return float(amperage_str) / 10, {
            "1": (0, "load normal"),
            "2": (2, "load low"),
            "3": (1, "load near over load"),
            "4": (2, "load over load"),
        }[device_state]

    parsed: Dict[str, Dict[str, Union[float, Tuple[float, Tuple[int, str]]]]] = {}
    device_info, bank_info, phase_info = string_table
    pdu_ident_name, power_str = device_info[0]
    device_name = "Device %s" % pdu_ident_name

    parsed.setdefault(device_name, {"power": float(power_str)})

    if len(device_info) == len(phase_info):
        parsed[device_name]["current"] = get_status_info(*phase_info[0][1:])
        return parsed

    if int(bank_info[0][0]):
        parsed[device_name]["current"] = get_status_info(*phase_info[0][1:])
        phase_info = phase_info[1:]
        name_part = "Bank"
    else:
        name_part = "Phase"

    for oid_end, amperage_str, device_state in phase_info:
        parsed.setdefault("%s %s" % (name_part, oid_end),
                          {"current": get_status_info(amperage_str, device_state)})

    return parsed


register.snmp_section(
    name="apc_rackpdu_power",
    parse_function=parse_apc_rackpdu_power,
    trees=[
        SNMPTree(
            base=".1.3.6.1.4.1.318.1.1.12.1",
            oids=[
                '1',  # rPDUIdentName
                '16',  # rPDUIdentDevicePowerWatts
            ],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.318.1.1.12.2.1",
            oids=[
                '4',  # rPDULoadDevNumBanks
            ],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.318.1.1.12.2.3.1.1",
            oids=[
                OIDEnd(),
                '2',  # rPDULoadStatusLoad
                '3',  # rPDULoadStatusLoadState
            ],
        ),
    ],
    detect=all_of(
        startswith(".1.3.6.1.2.1.1.1.0", 'apc web/snmp'),
        exists(".1.3.6.1.4.1.318.1.1.12.1.*"),
    ),
)
