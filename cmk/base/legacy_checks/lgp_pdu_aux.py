#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"

# Check has been developed using a Emerson Network Power Rack PDU Card
# Agent App Firmware Version  4.840.0
# Agent Boot Firmware Version 4.540.3
# FDM Version 1209
# GDD Version 45585

# Example info:
# [['10.1.1.1', '2'], ['10.1.2.1', '1'], ['10.1.3.1', '3'], ['10.1.3.2', '3'], ['15.1.1.1', 'SNSR: 1-1'], ['15.1.2.1', 'SNSR: 1-2'], ['15.1.3.1', 'SNSR: 1-3'], ['15.1.3.2', 'SNSR: 1-3'], ['20.1.1.1', 'RAD-LUNEPL-SEN7(80000000B080CF26)'], ['20.1.2.1', 'RAD-LUNEPL-SEN5(Rueckseite-oben)'], ['20.1.3.1', 'RAD-LUNEPL-SEN3(TuerRueckseite)'], ['20.1.3.2', 'RAD-LUNEPL-SEN1(TuerFront)'], ['25.1.1.1', ''], ['25.1.2.1', ''], ['25.1.3.1', ''], ['25.1.3.2', ''], ['30.1.1.1', ''], ['30.1.2.1', ''], ['30.1.3.1', ''], ['30.1.3.2', ''], ['35.1.1.1', '80000000B080CF26'], ['35.1.2.1', 'DD0000000DFAEA42'], ['35.1.3.1', 'EC00000013FBD820'], ['35.1.3.2', 'EC00000013FBD820'], ['40.1.2.1', '873'], ['50.1.2.1', '500'], ['55.1.2.1', '878'], ['60.1.2.1', '590'], ['65.1.2.1', '806'], ['70.1.2.1', '307'], ['75.1.2.1', '100'], ['80.1.2.1', '310'], ['85.1.2.1', '150'], ['90.1.2.1', '270'], ['95.1.1.1', '156'], ['100.1.1.1', '150'], ['105.1.1.1', '600'], ['110.1.1.1', '200'], ['115.1.1.1', '560'], ['120.1.3.1', '2'], ['120.1.3.2', '2'], ['125.1.3.1', '1'], ['125.1.3.2', '1']]

# Indexes in lgpPduAuxMeasTable are:
# 1. lgpPduEntryIndex
# 2. lgpPduAuxMeasSensorIndex
# 3. lgpPduAuxMeasSensorMeasurementIndex

#     10, # LIEBERT-GP-PDU-MIB::lgpPduAuxMeasType
#     15, # LIEBERT-GP-PDU-MIB::lgpPduAuxMeasSensorSysAssignLabel
#     20, # LIEBERT-GP-PDU-MIB::lgpPduAuxMeasUsrLabel
#     35, # LIEBERT-GP-PDU-MIB::lgpPduAuxMeasSensorSerialNum
#     70, # LIEBERT-GP-PDU-MIB::lgpPduAuxMeasTempDeg
#     75, # LIEBERT-GP-PDU-MIB::lgpPduAuxMeasTempThrshldUndrAlmDegC
#     80, # LIEBERT-GP-PDU-MIB::lgpPduAuxMeasTempThrshldOvrAlmDegC
#     85, # LIEBERT-GP-PDU-MIB::lgpPduAuxMeasTempThrshldUndrWarnDegC
#     90, # LIEBERT-GP-PDU-MIB::lgpPduAuxMeasTempThrshldOvrWarnDegC
#     95, # LIEBERT-GP-PDU-MIB::lgpPduAuxMeasHum
#    100, # LIEBERT-GP-PDU-MIB::lgpPduAuxMeasHumThrshldUndrAlm
#    105, # LIEBERT-GP-PDU-MIB::lgpPduAuxMeasHumThrshldOvrAlm
#    110, # LIEBERT-GP-PDU-MIB::lgpPduAuxMeasHumThrshldUndrWarn
#    115, # LIEBERT-GP-PDU-MIB::lgpPduAuxMeasHumThrshldOvrWarn
#    120, # LIEBERT-GP-PDU-MIB::lgpPduAuxMeasDrClosureState
#    125, # LIEBERT-GP-PDU-MIB::lgpPduAuxMeasDrClosureConfig

from collections.abc import Callable, Mapping

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import OIDEnd, SNMPTree, StringTable
from cmk.plugins.lgp.lib import DETECT_LGP

check_info = {}

lgp_pdu_aux_types = {
    "0": "UNSPEC",
    "1": "TEMP",
    "2": "HUM",
    "3": "DOOR",
    "4": "CONTACT",
}

lgp_pdu_aux_states = [
    "not-specified",
    "open",
    "closed",
]


def savefloat(f: str) -> float:
    """Tries to cast a string to an float and return it. In case this fails,
    it returns 0.0.

    Advice: Please don't use this function in new code. It is understood as
    bad style these days, because in case you get 0.0 back from this function,
    you can not know whether it is really 0.0 or something went wrong."""
    try:
        return float(f)
    except (TypeError, ValueError):
        return 0.0


def saveint(i: str) -> int:
    """Tries to cast a string to an integer and return it. In case this
    fails, it returns 0.

    Advice: Please don't use this function in new code. It is understood as
    bad style these days, because in case you get 0 back from this function,
    you can not know whether it is really 0 or something went wrong."""
    try:
        return int(i)
    except (TypeError, ValueError):
        return 0


_lgp_pdu_aux_fields: Mapping[str, tuple[Callable[[str], str | float | int], str]] = {
    # Index, Type, Factor, ID
    "10": (lambda x: lgp_pdu_aux_types.get(x, "UNHANDLED"), "Type"),
    "15": (str, "SystemLabel"),
    "20": (str, "UserLabel"),
    "35": (str, "SerialNumber"),
    "70": (lambda x: savefloat(x) * 0.1, "Temp"),
    "75": (lambda x: savefloat(x) * 0.1, "TempLowCrit"),
    "80": (lambda x: savefloat(x) * 0.1, "TempHighCrit"),
    "85": (lambda x: savefloat(x) * 0.1, "TempLowWarn"),
    "90": (lambda x: savefloat(x) * 0.1, "TempHighWarn"),
    "95": (lambda x: savefloat(x) * 0.1, "Hum"),
    "100": (lambda x: savefloat(x) * 0.1, "HumLowCrit"),
    "105": (lambda x: savefloat(x) * 0.1, "HumHighCrit"),
    "110": (lambda x: savefloat(x) * 0.1, "HumLowWarn"),
    "115": (lambda x: savefloat(x) * 0.1, "HumHighWarn"),
    "120": (saveint, "DoorState"),
    "125": (saveint, "DoorConfig"),
}


def lgp_pdu_aux_fmt(info):
    new_info = {}
    for oid, value in info:
        type_, id_ = oid.split(".", 1)
        if id_ not in new_info:
            new_info[id_] = {"TypeIndex": id_.split(".")[-1]}

        try:
            converter, key = _lgp_pdu_aux_fields[type_]
        except KeyError:
            continue

        new_info[id_][key] = converter(value)

    return new_info


def discover_lgp_pdu_aux(info):
    info = lgp_pdu_aux_fmt(info)
    inv = []
    for pdu in info.values():
        # Using SystemLabel as index. But it is not uniq in all cases.
        # Adding the Type-Index to prevent problems
        inv.append((pdu["Type"] + "-" + pdu["SystemLabel"] + "-" + pdu["TypeIndex"], None))
    return inv


def check_lgp_pdu_aux(item, params, info):
    info = lgp_pdu_aux_fmt(info)
    for pdu in info.values():
        if item == pdu["Type"] + "-" + pdu["SystemLabel"] + "-" + pdu["TypeIndex"]:
            state = 0
            output = []
            perfdata = []

            if pdu["UserLabel"] != "":
                output.append("Label: {} ({})".format(pdu["UserLabel"], pdu["SystemLabel"]))
            else:
                output.append("Label: " + pdu["SystemLabel"])

            def handle_type(ty, label, uom, pdu=pdu):
                state = 0
                perfdata = (
                    ty.lower(),
                    pdu[ty],
                    "{:0.2f}:{:0.2f}".format(pdu[ty + "LowWarn"], pdu[ty + "HighWarn"]),
                    "{:0.2f}:{:0.2f}".format(pdu[ty + "LowCrit"], pdu[ty + "HighCrit"]),
                )
                s_out = ""
                if pdu[ty] >= pdu[ty + "HighCrit"]:
                    state = 2
                    s_out = " >= %0.2f (!!)" % pdu[ty + "HighCrit"]
                elif pdu[ty] <= pdu[ty + "LowCrit"]:
                    state = 2
                    s_out = " <= %0.2f (!!)" % pdu[ty + "LowCrit"]
                elif pdu[ty] >= pdu[ty + "HighWarn"]:
                    state = 1
                    s_out = " >= %0.2f (!)" % pdu[ty + "HighWarn"]
                elif pdu[ty] <= pdu[ty + "LowWarn"]:
                    state = 1
                    s_out = " <= %0.2f (!)" % pdu[ty + "LowWarn"]

                return state, f"{label}: {pdu[ty]:0.2f}{uom}{s_out}", perfdata

            if pdu["Type"] == "TEMP":
                state, out, perf = handle_type("Temp", "Temperature", "C")
                output.append(out)
                perfdata.append(perf)

            elif pdu["Type"] == "HUM":
                state, out, perf = handle_type("Hum", "Humidity", "%")
                output.append(out)
                perfdata.append(perf)

            elif pdu["Type"] == "DOOR":
                # DoorConfig: 1 -> open, 0 -> disabled
                if pdu["DoorConfig"] == 1 and lgp_pdu_aux_states[pdu["DoorState"]] == "open":
                    state = 2
                    output.append("Door is %s (!!)" % lgp_pdu_aux_states[pdu["DoorState"]])
                else:
                    output.append("Door is %s" % lgp_pdu_aux_states[pdu["DoorState"]])

            return (state, ", ".join(output), perfdata)

    return (3, "Could not find given PDU.")


def parse_lgp_pdu_aux(string_table: StringTable) -> StringTable:
    return string_table


check_info["lgp_pdu_aux"] = LegacyCheckDefinition(
    name="lgp_pdu_aux",
    parse_function=parse_lgp_pdu_aux,
    detect=DETECT_LGP,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.476.1.42.3.8.60.15",
        oids=[OIDEnd(), "1"],
    ),
    service_name="Liebert PDU AUX %s",
    discovery_function=discover_lgp_pdu_aux,
    check_function=check_lgp_pdu_aux,
)
