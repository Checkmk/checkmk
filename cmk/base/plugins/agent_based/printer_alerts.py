#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Final, List, NamedTuple, Sequence

from .agent_based_api.v1 import register, Result, Service, SNMPTree, State
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable
from .utils.printer import DETECT_PRINTER


class Alert(NamedTuple):
    severity: str
    group: str
    group_index: str
    code: str
    description: str


Section = Sequence[Alert]

PRINTER_ALERTS_GROUP_MAP: Final = {
    "1": "other",
    "3": "hostResourcesMIBStorageTable",
    "4": "hostResourcesMIBDeviceTable",
    "5": "generalPrinter",
    "6": "cover",
    "7": "localization",
    "8": "input",
    "9": "output",
    "10": "marker",
    "11": "markerSupplies",
    "12": "markerColorant",
    "13": "mediaPath",
    "14": "channel",
    "15": "interpreter",
    "16": "consoleDisplayBuffer",
    "17": "consoleLights",
    "18": "alert",
    "30": "finDevice",
    "31": "finSypply",
    "32": "finSupplyMediaInput",
    "33": "finAttributeTable",
}

PRINTER_CODE_MAP: Final = {
    "1": ("other", State.OK),
    "2": ("unknown", State.WARN),
    "3": ("coverOpen", State.WARN),
    "4": ("coverClosed", State.OK),
    "5": ("interlockOpen", State.UNKNOWN),
    "6": ("interlockClosed", State.OK),
    "7": ("configurationChange", State.OK),
    "8": ("jam", State.CRIT),
    "9": ("subunitMissing", State.WARN),
    "10": ("subunitLifeAlmostOver", State.WARN),
    "11": ("subunitLifeOver", State.CRIT),
    "12": ("subunitAlmostEmpty", State.WARN),
    "13": ("subunitEmpty", State.WARN),
    "14": ("subunitAlmostFull", State.WARN),
    "15": ("subunitFull", State.WARN),
    "16": ("subunitNearLimit", State.WARN),
    "17": ("subunitAtLimit", State.CRIT),
    "18": ("subunitOpened", State.WARN),
    "19": ("subunitClosed", State.OK),
    "20": ("subunitTurnedOn", State.OK),
    "21": ("subunitTurnedOff", State.WARN),
    "22": ("subunitOffline", State.OK),
    "23": ("subunitPowerSaver", State.OK),
    "24": ("subunitWarmingUp", State.OK),
    "25": ("subunitAdded", State.OK),
    "26": ("subunitRemoved", State.UNKNOWN),
    "27": ("subunitResourceAdded", State.OK),
    "28": ("subunitResourceRemoved", State.WARN),
    "29": ("subunitRecoverableFailure", State.WARN),
    "30": ("subunitUnrecoverableFailure", State.CRIT),
    "31": ("subunitRecoverableStorageError", State.WARN),
    "32": ("subunitUnrecoverableStorageError", State.CRIT),
    "33": ("subunitMotorFailure", State.WARN),
    "34": ("subunitMemoryExhausted", State.WARN),
    "35": ("subunitUnderTemperature", State.OK),
    "36": ("subunitOverTemperature", State.OK),
    "37": ("subunitTimingFailure", State.OK),
    "38": ("subunitThermistorFailure", State.OK),
    "501": ("doorOpen", State.WARN),
    "502": ("doorClosed", State.OK),
    "503": ("powerUp", State.OK),
    "504": ("powerDown", State.OK),
    "505": ("printerNMSReset", State.OK),
    "506": ("printerManualReset", State.OK),
    "507": ("printerReadyToPrint", State.OK),
    "801": ("inputMediaTrayMissing", State.WARN),
    "802": ("inputMediaSizeChange", State.OK),
    "803": ("inputMediaWeightChange", State.OK),
    "804": ("inputMediaTypeChange", State.OK),
    "805": ("inputMediaColorChange", State.OK),
    "806": ("inputMediaFormPartsChange", State.OK),
    "807": ("inputMediaSupplyLow", State.OK),
    "808": ("inputMediaSupplyEmpty", State.OK),
    "809": ("inputMediaChangeRequest", State.OK),
    "810": ("inputManualInputRequest", State.OK),
    "811": ("inputTrayPositionFailure", State.WARN),
    "812": ("inputTrayElevationFailure", State.WARN),
    "813": ("inputCannotFeedSizeSelected", State.OK),
    "901": ("outputMediaTrayMissing", State.WARN),
    "902": ("outputMediaTrayAlmostFull", State.OK),
    "903": ("outputMediaTrayFull", State.WARN),
    "904": ("outputMailboxSelectFailure", State.WARN),
    "1001": ("markerFuserUnderTemperature", State.OK),
    "1002": ("markerFuserOverTemperature", State.OK),
    "1003": ("markerFuserTimingFailure", State.WARN),
    "1004": ("markerFuserThermistorFailure", State.WARN),
    "1005": ("markerAdjustingPrintQuality", State.OK),
    "1101": ("markerTonerEmpty", State.CRIT),
    "1102": ("markerInkEmpty", State.CRIT),
    "1103": ("markerPrintRibbonEmpty", State.CRIT),
    "1104": ("markerTonerAlmostEmpty", State.WARN),
    "1105": ("markerInkAlmostEmpty", State.WARN),
    "1106": ("markerPrintRibbonAlmostEmpty", State.OK),
    "1107": ("markerWasteTonerReceptacleAlmostFull", State.OK),
    "1108": ("markerWasteInkReceptacleAlmostFull", State.OK),
    "1109": ("markerWasteTonerReceptacleFull", State.CRIT),
    "1110": ("markerWasteInkReceptacleFull", State.CRIT),
    "1111": ("markerOpcLifeAlmostOver", State.OK),
    "1112": ("markerOpcLifeOver", State.CRIT),
    "1113": ("markerDeveloperAlmostEmpty", State.OK),
    "1114": ("markerDeveloperEmpty", State.CRIT),
    "1115": ("markerTonerCartridgeMissing", State.CRIT),
    "1301": ("mediaPathMediaTrayMissing", State.WARN),
    "1302": ("mediaPathMediaTrayAlmostFull", State.OK),
    "1303": ("mediaPathMediaTrayFull", State.CRIT),
    "1304": ("mediaPathCannotDuplexMediaSelected", State.OK),
    "1501": ("interpreterMemoryIncrease", State.OK),
    "1502": ("interpreterMemoryDecrease", State.OK),
    "1503": ("interpreterCartridgeAdded", State.OK),
    "1504": ("interpreterCartridgeDeleted", State.OK),
    "1505": ("interpreterResourceAdded", State.OK),
    "1506": ("interpreterResourceDeleted", State.OK),
    "1507": ("interpreterResourceUnavailable", State.UNKNOWN),
    "1509": ("interpreterComplexPageEncountered", State.OK),
}

PRINTER_ALERTS_TEXT_MAP: Final = {
    "Energiesparen": State.OK,
    "Sleep": State.OK,
}


def parse_printer_alerts(string_table: List[StringTable]) -> Section:
    return [Alert(*s) for s in string_table[0] if s[1:5] != ["0", "0", "0", ""]]


register.snmp_section(
    name="printer_alerts",
    detect=DETECT_PRINTER,
    parse_function=parse_printer_alerts,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.2.1.43.18.1.1",
            oids=[
                "2",
                "4",
                "5",
                "7",
                "8",
            ],
        ),
    ],
)


def discovery_printer_alerts(section: Section) -> DiscoveryResult:
    yield Service()


def check_printer_alerts(section: Section) -> CheckResult:
    if not section:
        yield Result(state=State.OK, summary="No alerts present")
        return

    sum_state = State.OK
    sum_txt = []
    for alert in section:
        unknown_code_msg = f"unknown alert code: {alert.code}"
        code_txt, state = PRINTER_CODE_MAP.get(alert.code, (unknown_code_msg, State.UNKNOWN))

        if alert.description in PRINTER_ALERTS_TEXT_MAP:
            state = PRINTER_ALERTS_TEXT_MAP[alert.description]
            if state != State.OK:
                sum_state = State(max(state.value, sum_state.value))
                sum_txt.append(alert.description)
            continue

        # Code not found -> take into account severity
        if state == State.UNKNOWN and alert.severity == "1":
            state = State.OK

        # determine the total(sum) state of the check
        if state == State.CRIT:
            sum_state = State.CRIT
        elif state == State.UNKNOWN and sum_state != State.CRIT:
            sum_state = State.UNKNOWN
        elif state.value > sum_state.value:
            sum_state = state

        # collect the check output
        unknown_group_msg = f"unknown alert group {alert.group}"
        info_txt = [PRINTER_ALERTS_GROUP_MAP.get(alert.group, unknown_group_msg)]

        if alert.group_index != "-1" and info_txt[0].startswith("unknown alert group"):
            info_txt.append(f"#{alert.group_index}")
        info_txt.append(": ")

        if alert.description != "":
            info_txt.append(alert.description)
        elif alert.code != "-1":
            info_txt.append(code_txt)

        sum_txt.append("".join(info_txt))

    if len(sum_txt) == 0:
        sum_txt.append("No alerts found")

    yield Result(state=sum_state, summary=", ".join(sum_txt))


register.check_plugin(
    name="printer_alerts",
    service_name="Alerts",
    discovery_function=discovery_printer_alerts,
    check_function=check_printer_alerts,
)
