#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Mapping, Sequence
from typing import Any

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    contains,
    DiscoveryResult,
    OIDEnd,
    Result,
    Service,
    SNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.lib.elphase import check_elphase
from cmk.plugins.lib.humidity import check_humidity
from cmk.plugins.lib.temperature import check_temperature, TempParamType

#   .--output--------------------------------------------------------------.
#   |                               _               _                      |
#   |                    ___  _   _| |_ _ __  _   _| |_                    |
#   |                   / _ \| | | | __| '_ \| | | | __|                   |
#   |                  | (_) | |_| | |_| |_) | |_| | |_                    |
#   |                   \___/ \__,_|\__| .__/ \__,_|\__|                   |
#   |                                  |_|                                 |
#   '----------------------------------------------------------------------'

# .1.3.6.1.4.1.31770.2.2.6.2.1.4.1.1 Inlet 1

# .1.3.6.1.4.1.31770.2.2.6.3.1.4.1.1.1 "00 00 00 00 FF FF 00 00 "
# .1.3.6.1.4.1.31770.2.2.6.3.1.4.1.1.2 "00 00 00 01 FF FF 00 00 "
# .1.3.6.1.4.1.31770.2.2.6.3.1.4.1.1.3 "00 00 00 02 FF FF 00 00 "

# .1.3.6.1.4.1.31770.2.2.6.6.1.7.1.1.1.0.0.1 "00 04 00 00 FF FF 00 00 "
# .1.3.6.1.4.1.31770.2.2.6.6.1.7.1.1.2.0.0.2 "00 04 00 01 FF FF 00 00 "
# .1.3.6.1.4.1.31770.2.2.6.6.1.7.1.1.3.0.0.3 "00 04 00 02 FF FF 00 00 "

# .1.3.6.1.4.1.31770.2.2.8.2.1.6.0.0.0.0.255.255.0.1 1 --> BACHMANN-bluenet2-MIB::bluenet2VariableType.'........'
# .1.3.6.1.4.1.31770.2.2.8.2.1.6.0.0.0.0.255.255.0.4 4 --> BACHMANN-bluenet2-MIB::bluenet2VariableType.'........'
# .1.3.6.1.4.1.31770.2.2.8.2.1.6.0.0.0.0.255.255.0.5 5 --> BACHMANN-bluenet2-MIB::bluenet2VariableType.'........'
# .1.3.6.1.4.1.31770.2.2.8.2.1.6.0.0.0.0.255.255.0.17 17 --> BACHMANN-bluenet2-MIB::bluenet2VariableType.'........'
# .1.3.6.1.4.1.31770.2.2.8.2.1.6.0.0.0.0.255.255.0.18 18 --> BACHMANN-bluenet2-MIB::bluenet2VariableType.'........'
# .1.3.6.1.4.1.31770.2.2.8.2.1.6.0.0.0.0.255.255.0.19 19 --> BACHMANN-bluenet2-MIB::bluenet2VariableType.'........'
# .1.3.6.1.4.1.31770.2.2.8.2.1.6.0.0.0.0.255.255.0.20 20 --> BACHMANN-bluenet2-MIB::bluenet2VariableType.'........'
# .1.3.6.1.4.1.31770.2.2.8.2.1.6.0.0.0.0.255.255.0.22 22 --> BACHMANN-bluenet2-MIB::bluenet2VariableType.'........'
# .1.3.6.1.4.1.31770.2.2.8.2.1.6.0.0.0.0.255.255.0.23 23 --> BACHMANN-bluenet2-MIB::bluenet2VariableType.'........'
# .1.3.6.1.4.1.31770.2.2.8.2.1.6.0.0.0.0.255.255.0.32 32 --> BACHMANN-bluenet2-MIB::bluenet2VariableType.'....... '
# .1.3.6.1.4.1.31770.2.2.8.2.1.6.0.0.0.0.255.255.0.34 34 --> BACHMANN-bluenet2-MIB::bluenet2VariableType.'......."'
# .1.3.6.1.4.1.31770.2.2.8.2.1.6.0.0.0.0.255.255.0.36 36 --> BACHMANN-bluenet2-MIB::bluenet2VariableType.'.......$'
# .1.3.6.1.4.1.31770.2.2.8.2.1.6.0.0.0.0.255.255.0.38 38 --> BACHMANN-bluenet2-MIB::bluenet2VariableType.'.......&'
# .1.3.6.1.4.1.31770.2.2.8.2.1.6.0.1.64.4.255.2.1.0 256 --> BACHMANN-bluenet2-MIB::bluenet2VariableType.'..@.....'
# .1.3.6.1.4.1.31770.2.2.8.2.1.6.0.1.64.4.255.2.1.1 257 --> BACHMANN-bluenet2-MIB::bluenet2VariableType.'..@.....'
# .1.3.6.1.4.1.31770.2.2.8.2.1.6.0.4.0.0.255.255.0.7 7 --> BACHMANN-BLUENET2-MIB::blueNet2VariableType.'........'
# .1.3.6.1.4.1.31770.2.2.8.2.1.6.0.4.0.0.255.255.0.8 8 --> BACHMANN-BLUENET2-MIB::blueNet2VariableType.'........'

# .1.3.6.1.4.1.31770.2.2.8.2.1.7.0.0.0.0.255.255.0.1 2 --> BACHMANN-bluenet2-MIB::bluenet2VariableStatus.'........'
# .1.3.6.1.4.1.31770.2.2.8.2.1.7.0.0.0.0.255.255.0.4 2 --> BACHMANN-bluenet2-MIB::bluenet2VariableStatus.'........'
# .1.3.6.1.4.1.31770.2.2.8.2.1.7.0.0.0.0.255.255.0.5 2 --> BACHMANN-bluenet2-MIB::bluenet2VariableStatus.'........'
# .1.3.6.1.4.1.31770.2.2.8.2.1.7.0.0.0.0.255.255.0.17 2 --> BACHMANN-bluenet2-MIB::bluenet2VariableStatus.'........'
# .1.3.6.1.4.1.31770.2.2.8.2.1.7.0.0.0.0.255.255.0.18 2 --> BACHMANN-bluenet2-MIB::bluenet2VariableStatus.'........'
# .1.3.6.1.4.1.31770.2.2.8.2.1.7.0.0.0.0.255.255.0.19 2 --> BACHMANN-bluenet2-MIB::bluenet2VariableStatus.'........'
# .1.3.6.1.4.1.31770.2.2.8.2.1.7.0.0.0.0.255.255.0.20 2 --> BACHMANN-bluenet2-MIB::bluenet2VariableStatus.'........'
# .1.3.6.1.4.1.31770.2.2.8.2.1.7.0.0.0.0.255.255.0.22 2 --> BACHMANN-bluenet2-MIB::bluenet2VariableStatus.'........'
# .1.3.6.1.4.1.31770.2.2.8.2.1.7.0.0.0.0.255.255.0.23 2 --> BACHMANN-bluenet2-MIB::bluenet2VariableStatus.'........'
# .1.3.6.1.4.1.31770.2.2.8.2.1.7.0.0.0.0.255.255.0.32 2 --> BACHMANN-bluenet2-MIB::bluenet2VariableStatus.'....... '
# .1.3.6.1.4.1.31770.2.2.8.2.1.7.0.0.0.0.255.255.0.34 2 --> BACHMANN-bluenet2-MIB::bluenet2VariableStatus.'......."'
# .1.3.6.1.4.1.31770.2.2.8.2.1.7.0.0.0.0.255.255.0.36 2 --> BACHMANN-bluenet2-MIB::bluenet2VariableStatus.'.......$'
# .1.3.6.1.4.1.31770.2.2.8.2.1.7.0.0.0.0.255.255.0.38 2 --> BACHMANN-bluenet2-MIB::bluenet2VariableStatus.'.......&'
# .1.3.6.1.4.1.31770.2.2.8.2.1.7.0.1.64.4.255.2.1.0 2 --> BACHMANN-bluenet2-MIB::bluenet2VariableStatus.'..@.....'
# .1.3.6.1.4.1.31770.2.2.8.2.1.7.0.1.64.4.255.2.1.1 2 --> BACHMANN-bluenet2-MIB::bluenet2VariableStatus.'..@.....'
# .1.3.6.1.4.1.31770.2.2.8.2.1.7.0.4.0.0.255.255.0.7 2 --> BACHMANN-BLUENET2-MIB::blueNet2VariableStatus.'........'
# .1.3.6.1.4.1.31770.2.2.8.2.1.7.0.4.0.0.255.255.0.8 2 --> BACHMANN-BLUENET2-MIB::blueNet2VariableStatus.'........'

# .1.3.6.1.4.1.31770.2.2.8.2.1.9.0.0.0.0.255.255.0.1 -2 --> BACHMANN-bluenet2-MIB::bluenet2VariableScaling.'........'
# .1.3.6.1.4.1.31770.2.2.8.2.1.9.0.0.0.0.255.255.0.4 -2 --> BACHMANN-bluenet2-MIB::bluenet2VariableScaling.'........'
# .1.3.6.1.4.1.31770.2.2.8.2.1.9.0.0.0.0.255.255.0.5 -2 --> BACHMANN-bluenet2-MIB::bluenet2VariableScaling.'........'
# .1.3.6.1.4.1.31770.2.2.8.2.1.9.0.0.0.0.255.255.0.17 -3 --> BACHMANN-bluenet2-MIB::bluenet2VariableScaling.'........'
# .1.3.6.1.4.1.31770.2.2.8.2.1.9.0.0.0.0.255.255.0.18 -1 --> BACHMANN-bluenet2-MIB::bluenet2VariableScaling.'........'
# .1.3.6.1.4.1.31770.2.2.8.2.1.9.0.0.0.0.255.255.0.19 -1 --> BACHMANN-bluenet2-MIB::bluenet2VariableScaling.'........'
# .1.3.6.1.4.1.31770.2.2.8.2.1.9.0.0.0.0.255.255.0.20 -1 --> BACHMANN-bluenet2-MIB::bluenet2VariableScaling.'........'
# .1.3.6.1.4.1.31770.2.2.8.2.1.9.0.0.0.0.255.255.0.22 -1 --> BACHMANN-bluenet2-MIB::bluenet2VariableScaling.'........'
# .1.3.6.1.4.1.31770.2.2.8.2.1.9.0.0.0.0.255.255.0.23 -2 --> BACHMANN-bluenet2-MIB::bluenet2VariableScaling.'........'
# .1.3.6.1.4.1.31770.2.2.8.2.1.9.0.0.0.0.255.255.0.32 -4 --> BACHMANN-bluenet2-MIB::bluenet2VariableScaling.'....... '
# .1.3.6.1.4.1.31770.2.2.8.2.1.9.0.0.0.0.255.255.0.34 -4 --> BACHMANN-bluenet2-MIB::bluenet2VariableScaling.'......."'
# .1.3.6.1.4.1.31770.2.2.8.2.1.9.0.0.0.0.255.255.0.36 -4 --> BACHMANN-bluenet2-MIB::bluenet2VariableScaling.'.......$'
# .1.3.6.1.4.1.31770.2.2.8.2.1.9.0.0.0.0.255.255.0.38 -4 --> BACHMANN-bluenet2-MIB::bluenet2VariableScaling.'.......&'
# .1.3.6.1.4.1.31770.2.2.8.2.1.9.0.1.64.4.255.2.1.0 -1 --> BACHMANN-bluenet2-MIB::bluenet2VariableScaling.'..@.....'
# .1.3.6.1.4.1.31770.2.2.8.2.1.9.0.1.64.4.255.2.1.1 -1 --> BACHMANN-bluenet2-MIB::bluenet2VariableScaling.'..@.....'
# .1.3.6.1.4.1.31770.2.2.8.2.1.9.0.4.0.0.255.255.0.7 -1 --> BACHMANN-BLUENET2-MIB::blueNet2VariableScaling.'........'
# .1.3.6.1.4.1.31770.2.2.8.2.1.9.0.4.0.0.255.255.0.8 -1 --> BACHMANN-BLUENET2-MIB::blueNet2VariableScaling.'........'

# .1.3.6.1.4.1.31770.2.2.8.4.1.5.0.0.0.1.255.255.0.1 23410 --> BACHMANN-bluenet2-MIB::bluenet2VariableDataValue.'........'
# .1.3.6.1.4.1.31770.2.2.8.4.1.5.0.0.0.1.255.255.0.4 95 --> BACHMANN-bluenet2-MIB::bluenet2VariableDataValue.'........'
# .1.3.6.1.4.1.31770.2.2.8.4.1.5.0.0.0.1.255.255.0.5 351 --> BACHMANN-bluenet2-MIB::bluenet2VariableDataValue.'........'
# .1.3.6.1.4.1.31770.2.2.8.4.1.5.0.0.0.1.255.255.0.17 -717 --> BACHMANN-bluenet2-MIB::bluenet2VariableDataValue.'........'
# .1.3.6.1.4.1.31770.2.2.8.4.1.5.0.0.0.1.255.255.0.18 2234 --> BACHMANN-bluenet2-MIB::bluenet2VariableDataValue.'........'
# .1.3.6.1.4.1.31770.2.2.8.4.1.5.0.0.0.1.255.255.0.19 1602 --> BACHMANN-bluenet2-MIB::bluenet2VariableDataValue.'........'
# .1.3.6.1.4.1.31770.2.2.8.4.1.5.0.0.0.1.255.255.0.20 5180 --> BACHMANN-bluenet2-MIB::bluenet2VariableDataValue.'........'
# .1.3.6.1.4.1.31770.2.2.8.4.1.5.0.0.0.1.255.255.0.22 -1571 --> BACHMANN-bluenet2-MIB::bluenet2VariableDataValue.'........'
# .1.3.6.1.4.1.31770.2.2.8.4.1.5.0.0.0.1.255.255.0.23 4997 --> BACHMANN-bluenet2-MIB::bluenet2VariableDataValue.'........'
# .1.3.6.1.4.1.31770.2.2.8.4.1.5.0.0.0.1.255.255.0.32 2407491 --> BACHMANN-bluenet2-MIB::bluenet2VariableDataValue.'....... '
# .1.3.6.1.4.1.31770.2.2.8.4.1.5.0.0.0.1.255.255.0.34 1302485 --> BACHMANN-bluenet2-MIB::bluenet2VariableDataValue.'......."'
# .1.3.6.1.4.1.31770.2.2.8.4.1.5.0.0.0.1.255.255.0.36 1842643 --> BACHMANN-bluenet2-MIB::bluenet2VariableDataValue.'.......$'
# .1.3.6.1.4.1.31770.2.2.8.4.1.5.0.0.0.1.255.255.0.38 1842643 --> BACHMANN-bluenet2-MIB::bluenet2VariableDataValue.'.......&'
# .1.3.6.1.4.1.31770.2.2.8.4.1.5.0.1.64.4.255.2.1.0 260 --> BACHMANN-bluenet2-MIB::bluenet2VariableDataValue.'..@.....'
# .1.3.6.1.4.1.31770.2.2.8.4.1.5.0.1.64.4.255.2.1.1 369 --> BACHMANN-bluenet2-MIB::bluenet2VariableDataValue.'..@.....'
# .1.3.6.1.4.1.31770.2.2.8.4.1.5.0.4.0.0.255.255.0.7 16 --> BACHMANN-BLUENET2-MIB::blueNet2VariableDataValue.'........'
# .1.3.6.1.4.1.31770.2.2.8.4.1.5.0.4.0.0.255.255.0.8 0 --> BACHMANN-BLUENET2-MIB::blueNet2VariableDataValue.'........'

# .
#   .--phases--------------------------------------------------------------.
#   |                         _                                            |
#   |                   _ __ | |__   __ _ ___  ___  ___                    |
#   |                  | '_ \| '_ \ / _` / __|/ _ \/ __|                   |
#   |                  | |_) | | | | (_| \__ \  __/\__ \                   |
#   |                  | .__/|_| |_|\__,_|___/\___||___/                   |
#   |                  |_|                                                 |
#   +----------------------------------------------------------------------+
#   |                            main check                                |
#   '----------------------------------------------------------------------'


def parse_bluenet2_powerrail(
    string_table: Sequence[StringTable],
) -> dict:
    map_status = {
        "0": (0, "expected"),
        "1": (3, "undefined"),
        "2": (0, "OK"),
        "3": (2, "error high"),
        "4": (2, "error low"),
        "5": (1, "warning high"),
        "6": (1, "warning low"),
        "7": (2, "lost"),
        "8": (1, "deactivate"),
        "9": (2, "on alarm identidy"),
        "10": (2, "off alarm identify"),
        "11": (2, "on alarm"),
        "12": (2, "off alarm"),
        "13": (1, "on warning identify"),
        "14": (1, "off warning identify"),
        "15": (1, "on warning"),
        "16": (1, "off warning"),
        "17": (0, "on identify"),
        "18": (0, "off identify"),
        "19": (0, "on"),
        "20": (1, "off"),
        "21": (2, "on child alarm"),
        "22": (2, "off child alarm"),
        "23": (1, "on child warning"),
        "24": (1, "off child warning"),
        "25": (2, "child alarm"),
        "26": (1, "child warning"),
        "27": (2, "lost child"),
        "36": (1, "update in progress"),
        "37": (2, "update error"),
        "38": (1, "ongoing switch"),
        "39": (2, "high"),
        "40": (1, "low"),
        "41": (2, "alarm"),
        "42": (1, "warning"),
        "43": (0, "ok"),
        "44": (1, "disabled"),
        "45": (1, "fw version too new"),
    }

    map_phase_types = {
        "1": ("phases", "Phase", "voltage"),
        "4": ("phases", "Phase", "current"),
        "18": ("phases", "Phase", "appower"),
        "19": ("phases", "Phase", "power"),
        "23": ("phases", "Phase", "frequency"),
        "7": ("rcm_phases", "RCM Phase", "differential_current_ac"),
        "8": ("rcm_phases", "RCM Phase", "differential_current_dc"),
        "9": ("inlet", "Neutral Current", "current"),
    }

    map_sensor_types = {
        "256": "temp",
        "257": "humidity",
    }

    def get_item_name(descr, index_str):
        return "%s %d" % (descr, int(index_str) + 1)

    def get_pdu_name(pdu_info):
        if pdu_info == "0":
            return "Master"
        return "PDU %s" % pdu_info

    oid_sections = [(0, "inlet"), (1, "phases"), (2, "rcm_phases"), (4, "sockets"), (5, "fuses")]

    pre_parsed: dict[str, dict[str, dict[str, dict[str, str]]]] = {}
    for oidend, _guid, _name, _friendly_name in string_table[0]:
        pre_parsed[oidend] = {}
        for index, what in oid_sections:
            pre_parsed[oidend][what] = {}

    for index, what in oid_sections:
        for oidend, identifier, name, friendly_name in string_table[index]:
            inlet_id = ".".join(oidend.split(".")[:2])
            if inlet_id in pre_parsed:
                pre_parsed[inlet_id][what][".".join([str(ord(x)) for x in identifier][:-1])] = {
                    "id": name,
                    "name": friendly_name,
                }

    parsed: dict[str, dict[str, dict[str, Any]]] = {"sensors": {}}
    for index, what in oid_sections:
        parsed[what] = {}
    for oidend, ty, status, exponent_str, reading_str in string_table[3]:
        status_info = map_status[status]
        reading = float(reading_str) * 10 ** int(exponent_str)
        oid_info = oidend.split(".")
        identifier = ".".join(oid_info[:-1])

        if ty in map_phase_types:
            phase_ty, phase_txt, what = map_phase_types[ty]
            for inlet_id, inlet_info in pre_parsed.items():
                if identifier in inlet_info[phase_ty].keys():
                    phase_name = get_item_name(f"{inlet_id} {phase_txt}", oid_info[3])
                    parsed[phase_ty].setdefault(phase_name, inlet_info[phase_ty][identifier])
                    parsed[phase_ty][phase_name].setdefault(what, (reading, status_info))
                if identifier in inlet_info["sockets"].keys():
                    socket_name = "{} {}".format(inlet_id, inlet_info["sockets"][identifier]["id"])
                    parsed["sockets"].setdefault(socket_name, inlet_info["sockets"][identifier])
                    parsed["sockets"][socket_name].setdefault(what, (reading, status_info))
                if identifier in inlet_info["fuses"].keys():
                    phase_id = identifier.split(".")[3]
                    fuse_name = "{}.{} {}".format(
                        inlet_id,
                        phase_id,
                        inlet_info["fuses"][identifier]["id"],
                    )
                    parsed["fuses"].setdefault(fuse_name, inlet_info["fuses"][identifier])
                    parsed["fuses"][fuse_name].setdefault(what, (reading, status_info))

        elif ty in map_sensor_types:
            # https://www.bachmann.com/fileadmin/05a_Downloads/BlueNet/BlueNet_BN3000_-_BN7500_V2.02.XX_Bedienungsanleitung_DE_Rev_01.pdf
            # Example of OID_END: ...0.1.64.4.255.2.1.0
            # 0   * number of pdu (pdu 0 -> Master PDU, 1, 2, 3,... -> Slave PDU)
            # 1     sensor type (0: electrical, 1: external sensor, 4: rcm)
            # 64    sensor hardware address (64: combination sensor, 72: temperature sensor, 56: GPIO module)
            # 4   * channel number of internal multiplexer (channel 4, 5)
            # 255 * channel number of external multiplexer (channel 255, 1, 2, 4, 8)
            # 2     external sensor type (2: combination sensor, 1: temperature sensor, 3: GPIO module)
            # 1.0   two byte key definition:
            #           1.0: temperature, 1.1: humidity 1.10:dewpoint
            #           1.2-1.5 GPIO in 1-4
            #           1.6-1.9 GPIO out 1-4
            # * becomes part of the item in order to make it unique
            sensor_name = f"Sensor {get_pdu_name(oid_info[0])} {oid_info[3]}/{oid_info[4]}"
            inst = parsed["sensors"].setdefault(map_sensor_types[ty], {})
            inst.setdefault(sensor_name, (reading, status_info))

    return parsed


snmp_section_bluenet2_powerrail = SNMPSection(
    name="bluenet2_powerrail",
    detect=contains(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.31770.2.1"),
    parse_function=parse_bluenet2_powerrail,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.31770.2.2.6.2.1",
            oids=[
                OIDEnd(),
                "3",  # blueNet2CircuitGuid
                "4",  # blueNet2CircuitName
                "5",  # blueNet2CircuitFriendlyName
            ],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.31770.2.2.6.3.1",
            oids=[
                OIDEnd(),
                "4",  # blueNet2PhaseGuid
                "5",  # blueNet2PhaseName
                "6",  # blueNet2PhaseFriendlyName
            ],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.31770.2.2.6.6.1",
            oids=[
                OIDEnd(),
                "7",  # blueNet2RcmGuid
                "8",  # blueNet2RcmName
                "9",  # blueNet2RcmFriendlyName
            ],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.31770.2.2.8",
            oids=[
                OIDEnd(),
                "2.1.6",  # bluenet2VariableType
                "2.1.7",  # bluenet2VariableStatus
                "2.1.9",  # bluenet2VariableScaling
                "4.1.5",  # bluenet2VariableDataValue
            ],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.31770.2.2.6.5.1",
            oids=[
                OIDEnd(),
                "6",  # blueNet2SocketGuid
                "7",  # blueNet2SocketName
                "8",  # blueNet2SocketFriendlyName
            ],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.31770.2.2.6.4.1",
            oids=[
                OIDEnd(),
                "5",  # blueNet2FuseGuid
                "6",  # blueNet2FuseName
                "7",  # blueNet2FuseFriendlyName
            ],
        ),
    ],
)


def discover_bluenet2_powerrail_phases(section: dict) -> DiscoveryResult:
    for key in section["phases"]:
        yield Service(item=key)


def check_bluenet2_powerrail_phases(
    item: str, params: Mapping[str, Any], section: dict
) -> CheckResult:
    yield from check_elphase(item, params, section["phases"])


check_plugin_bluenet2_powerrail = CheckPlugin(
    name="bluenet2_powerrail",
    sections=["bluenet2_powerrail"],
    service_name="Inlet %s",
    discovery_function=discover_bluenet2_powerrail_phases,
    check_function=check_bluenet2_powerrail_phases,
    check_ruleset_name="el_inphase",
    check_default_parameters={},
)

# .
#   .--RCM phases----------------------------------------------------------.
#   |        ____   ____ __  __         _                                  |
#   |       |  _ \ / ___|  \/  |  _ __ | |__   __ _ ___  ___  ___          |
#   |       | |_) | |   | |\/| | | '_ \| '_ \ / _` / __|/ _ \/ __|         |
#   |       |  _ <| |___| |  | | | |_) | | | | (_| \__ \  __/\__ \         |
#   |       |_| \_\\____|_|  |_| | .__/|_| |_|\__,_|___/\___||___/         |
#   |                            |_|                                       |
#   '----------------------------------------------------------------------'


def discover_bluenet2_powerrail_rcm_phases(section: dict) -> DiscoveryResult:
    for key in section["rcm_phases"]:
        yield Service(item=key)


def check_bluenet2_powerrail_rcm_phases(
    item: str, params: Mapping[str, Any], section: dict
) -> CheckResult:
    yield from check_elphase(item, params, section["rcm_phases"])


check_plugin_bluenet2_powerrail_rcm = CheckPlugin(
    name="bluenet2_powerrail_rcm",
    sections=["bluenet2_powerrail"],
    service_name="Inlet %s",
    discovery_function=discover_bluenet2_powerrail_rcm_phases,
    check_function=check_bluenet2_powerrail_rcm_phases,
    check_ruleset_name="el_inphase",
    check_default_parameters={
        # Suggested by customer
        "differential_current_ac": (3.5, 30.0),
        "differential_current_dc": (70.0, 100.0),
    },
)

# .
#   .--sockets-------------------------------------------------------------.
#   |                                  _        _                          |
#   |                   ___  ___   ___| | _____| |_ ___                    |
#   |                  / __|/ _ \ / __| |/ / _ \ __/ __|                   |
#   |                  \__ \ (_) | (__|   <  __/ |_\__ \                   |
#   |                  |___/\___/ \___|_|\_\___|\__|___/                   |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'


def discover_bluenet2_powerrail_sockets(section: dict) -> DiscoveryResult:
    for key in section["sockets"]:
        yield Service(item=key)


def check_bluenet2_powerrail_sockets(
    item: str, params: Mapping[str, Any], section: dict
) -> CheckResult:
    yield from check_elphase(item, params, section["sockets"])


check_plugin_bluenet2_powerrail_sockets = CheckPlugin(
    name="bluenet2_powerrail_sockets",
    sections=["bluenet2_powerrail"],
    service_name="Socket %s",
    discovery_function=discover_bluenet2_powerrail_sockets,
    check_function=check_bluenet2_powerrail_sockets,
    check_ruleset_name="ups_outphase",
    check_default_parameters={},
)

# .
#   .--fuses---------------------------------------------------------------.
#   |                        __                                            |
#   |                       / _|_   _ ___  ___  ___                        |
#   |                      | |_| | | / __|/ _ \/ __|                       |
#   |                      |  _| |_| \__ \  __/\__ \                       |
#   |                      |_|  \__,_|___/\___||___/                       |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'


def discover_bluenet2_powerrail_fuses(section: dict) -> DiscoveryResult:
    for key in section["fuses"]:
        yield Service(item=key)


def check_bluenet2_powerrail_fuses(
    item: str, params: Mapping[str, Any], section: dict
) -> CheckResult:
    yield from check_elphase(item, params, section["fuses"])


check_plugin_bluenet2_powerrail_fuses = CheckPlugin(
    name="bluenet2_powerrail_fuses",
    sections=["bluenet2_powerrail"],
    service_name="Fuse %s",
    discovery_function=discover_bluenet2_powerrail_fuses,
    check_function=check_bluenet2_powerrail_fuses,
    check_ruleset_name="ups_outphase",
    check_default_parameters={},
)

# .
#   .--inlet---------------------------------------------------------------.
#   |                         _       _      _                             |
#   |                        (_)_ __ | | ___| |_                           |
#   |                        | | '_ \| |/ _ \ __|                          |
#   |                        | | | | | |  __/ |_                           |
#   |                        |_|_| |_|_|\___|\__|                          |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'


def discover_bluenet2_powerrail_inlet(section: dict) -> DiscoveryResult:
    for key in section["inlet"]:
        yield Service(item=key)


def check_bluenet2_powerrail_inlet(
    item: str, params: Mapping[str, Any], section: dict
) -> CheckResult:
    yield from check_elphase(item, params, section["inlet"])


check_plugin_bluenet2_powerrail_inlet = CheckPlugin(
    name="bluenet2_powerrail_inlet",
    sections=["bluenet2_powerrail"],
    service_name="Inlet %s",
    discovery_function=discover_bluenet2_powerrail_inlet,
    check_function=check_bluenet2_powerrail_inlet,
    check_ruleset_name="el_inphase",
    check_default_parameters={},
)

# .
#   .--temperature---------------------------------------------------------.
#   |      _                                      _                        |
#   |     | |_ ___ _ __ ___  _ __   ___ _ __ __ _| |_ _   _ _ __ ___       |
#   |     | __/ _ \ '_ ` _ \| '_ \ / _ \ '__/ _` | __| | | | '__/ _ \      |
#   |     | ||  __/ | | | | | |_) |  __/ | | (_| | |_| |_| | | |  __/      |
#   |      \__\___|_| |_| |_| .__/ \___|_|  \__,_|\__|\__,_|_|  \___|      |
#   |                       |_|                                            |
#   '----------------------------------------------------------------------'


def discover_bluenet2_powerrail_temp(section: dict) -> DiscoveryResult:
    for item in section["sensors"].get("temp", {}):
        yield Service(item=item)


def check_bluenet2_powerrail_temp(item: str, params: TempParamType, section: dict) -> CheckResult:
    if item in section["sensors"].get("temp", {}):
        reading, (state, state_readable) = section["sensors"]["temp"][item]
        yield from check_temperature(
            reading,
            params,
            dev_status=state,
            dev_status_name=state_readable,
        )


check_plugin_bluenet2_powerrail_temp = CheckPlugin(
    name="bluenet2_powerrail_temp",
    sections=["bluenet2_powerrail"],
    service_name="Temperature %s",
    discovery_function=discover_bluenet2_powerrail_temp,
    check_function=check_bluenet2_powerrail_temp,
    check_ruleset_name="temperature",
    check_default_parameters={
        # Suggested by customer
        "levels": (30.0, 35.0),
    },
)

# .
#   .--humidity------------------------------------------------------------.
#   |              _                     _     _ _ _                       |
#   |             | |__  _   _ _ __ ___ (_) __| (_) |_ _   _               |
#   |             | '_ \| | | | '_ ` _ \| |/ _` | | __| | | |              |
#   |             | | | | |_| | | | | | | | (_| | | |_| |_| |              |
#   |             |_| |_|\__,_|_| |_| |_|_|\__,_|_|\__|\__, |              |
#   |                                                  |___/               |
#   '----------------------------------------------------------------------'


def discover_bluenet2_powerrail_humidity(section: dict) -> DiscoveryResult:
    for item in section["sensors"].get("humidity", {}):
        yield Service(item=item)


def check_bluenet2_powerrail_humidity(
    item: str, params: Mapping[str, Any], section: dict
) -> CheckResult:
    if item in section["sensors"].get("humidity", {}):
        reading, (state, state_readable) = section["sensors"]["humidity"][item]
        yield from check_humidity(reading, params)
        yield Result(
            state=State(state),
            summary=state_readable,
        )


check_plugin_bluenet2_powerrail_humidity = CheckPlugin(
    name="bluenet2_powerrail_humidity",
    sections=["bluenet2_powerrail"],
    service_name="Humidity %s",
    discovery_function=discover_bluenet2_powerrail_humidity,
    check_function=check_bluenet2_powerrail_humidity,
    check_ruleset_name="humidity",
    check_default_parameters={
        # Suggested by customer
        "levels": (75.0, 80.0),
        "levels_lower": (5.0, 8.0),
    },
)
