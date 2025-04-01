#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# snmp_info
# .1.3.6.1.4.1.2800.2.1.3                 < AirLaser Status

# Migrate to factory settings?


from collections.abc import Mapping, Sequence
from typing import Any

from cmk.agent_based.v2 import (
    all_of,
    CheckPlugin,
    CheckResult,
    contains,
    DiscoveryResult,
    exists,
    Metric,
    Result,
    Service,
    SNMPSection,
    SNMPTree,
    State,
    StringTable,
)

airlaser_default_levels = {
    "opttxTempValue": (60, 80),
    "chassisTempValue": (60, 70),
    "chassisFrontScreenTempValue": (40, 55),
    "optrxTempValue": (50, 60),
    "apmodTempValue": (60, 70),
}


Section = tuple[StringTable, Mapping[str, Mapping[str, tuple[str | int, str, int]]]]


def saveint(i: str | int) -> int:
    """Tries to cast a string to an integer and return it. In case this
    fails, it returns 0.

    Advice: Please don't use this function in new code. It is understood as
    bad style these days, because in case you get 0 back from this function,
    you can not know whether it is really 0 or something went wrong."""
    try:
        return int(i)
    except (TypeError, ValueError):
        return 0


def parse_cbl_airlaser(string_table: Sequence[StringTable]) -> Section | None:
    if not all(string_table):
        return None

    airlaser_status_names = {
        0: "undefined",
        1: "active",
        2: "standby",
        3: "warning",
        4: "failure",
        5: "not_installed",
    }

    # I have my own little MIB right here, their MIB is
    # just a long list, not structured.
    airlaser_sensors = {
        "chassis": {
            # Name of OID,    Value,    specific OID (not used), Position in SNMP data
            "chassisFrontScreenTempStatus": (None, "2.1.1.0", 0),
            "chassisFrontScreenTempValue": (None, "2.1.2.0", 1),
            "chassisHeatingStatus": (None, "2.1.7.0", 6),
            "chassisTempStatus": (None, "2.1.8.0", 7),
            "chassisTempValue": (None, "2.1.9.0", 8),
            "chassisFan1Status": (None, "2.1.10.0", 9),
            "chassisFan2Status": (None, "2.1.12.0", 11),
        },
        "power": {
            "psStatus48V": (None, "2.2.2.0", 1),
            "psStatus230V": (None, "2.2.3.0", 2),
            "psStatus5V": (None, "2.2.4.0", 3),
            "psStatus3V3": (None, "2.2.8.0", 7),
            "psStatus2V5": (None, "2.2.12.0", 11),
        },
        "module": {
            "apmodTempStatus": (None, "2.3.6.0", 5),
            "apmodTempValue": (None, "2.3.7.0", 6),
        },
        "opttx": {
            "opttxTempValue": (None, "2.4.3.0", 2),
            "opttxStatusTemp": (None, "2.4.4.0", 3),
        },
        "optrx": {
            "optrxStatusTemp": (None, "2.5.3.0", 2),
            # this is mislabeled "optrxValueTemp"
            "optrxTempValue": (None, "2.5.4.0", 3),
            # "optrxOptValue"
            # .1.3.6.1.4.1.2800.2.2.5.8.0  -10
            # "optrxOptMargin"
            # .1.3.6.1.4.1.2800.2.2.5.9.0  22
        },
    }

    # load the info into a dict separated by the different MIB regions
    # Selfest (info[0] is not handled here.
    data = {
        "chassis": string_table[1],
        "power": string_table[2],
        "module": string_table[3],
        "opttx": string_table[4],
        "optrx": string_table[5],
    }

    # update values from one dict into the other by picking the "offsetted" values
    # (optimize at will, if we can make it one-dict-for-all then we 100% sanitized their MIB)
    return string_table[0], {
        hwclass: {
            sensor: (
                (
                    airlaser_status_names[int(data[hwclass][offset][0])]
                    if "Status" in sensor
                    else saveint(data[hwclass][offset][0])
                ),
                sub_oid,
                offset,
            )
            for sensor, (_dummy, sub_oid, offset) in sensors.items()
        }
        for hwclass, sensors in airlaser_sensors.items()
    }


# TODO: use check_levels!
def check_cbl_airlaser_hw(params: Mapping[str, Any], section: Section) -> CheckResult:
    _selftest, sensors_data = section

    state = State.OK
    msgtxt = ""
    perfdata = []

    for sensors in sensors_data.values():
        for sensor, s in sensors.items():
            val = s[0]
            if sensor.lower().endswith("value"):
                val = saveint(val)
                if sensor in params:
                    warn, crit = params[sensor]
                    perfdata.append(
                        Metric(str(sensor), float(val), levels=(warn, crit), boundaries=(0, 90))
                    )
                    if val > crit:
                        state = State.CRIT
                    elif val > warn:
                        state = State.worst(state, State.WARN)
                else:
                    perfdata.append(Metric(str(sensor), float(val), boundaries=(0, 90)))

            # HACK: for the main PSUs the status 3 is not "warning" but
            # not_detected  (3)
            if sensor in ["psStatus48V", "psStatus230V"] and val == "warning":
                pass

            elif val == "failure":
                state = State.CRIT
            elif val == "warning":
                state = State.worst(state, State.WARN)
            # go here if no explicit error occurred,
            # no handling undefined and not_installed
            else:
                continue
            if state is not State.OK:
                msgtxt = (
                    msgtxt
                    + f"Sensor {sensor} {val}"
                    + {State.WARN: "!", State.CRIT: "!!", State.UNKNOWN: "!!!"}[state]
                    + " "
                )

    if state is State.OK:
        msgtxt = "All sensors OK"

    yield Result(state=state, summary=msgtxt)
    yield from perfdata


def inventory_cbl_airlaser(section: Section) -> DiscoveryResult:
    # start passing parameters, but since we might also need some for optics
    # this may change to using factory settings.
    # Or we just hardcode the margins we got from the vendor.
    yield Service(parameters=airlaser_default_levels)


def check_cbl_airlaser_status(section: Section) -> CheckResult:
    selftest, _sensors_data = section
    status = selftest[0][0]

    if status == "1":
        yield Result(state=State.OK, summary="Airlaser: normal operation")
        return
    if status == "2":
        yield Result(state=State.WARN, summary="Airlaser: testing mode")
        return
    if status == "3":
        yield Result(state=State.WARN, summary="Airlaser: warning condition")
        return
    if status == "4":
        yield Result(state=State.CRIT, summary="Airlaser: a component has failed self-tests")
        return

    yield Result(state=State.UNKNOWN, summary="Unknown data from agent")
    return


snmp_section_cbl_airlaser = SNMPSection(
    name="cbl_airlaser",
    detect=all_of(contains(".1.3.6.1.2.1.1.1.0", "airlaser"), exists(".1.3.6.1.4.1.2800.2.1.1.0")),
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.2800.2.1",
            oids=["3"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.2800.2.2",
            oids=["1"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.2800.2.2",
            oids=["2"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.2800.2.2",
            oids=["3"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.2800.2.2",
            oids=["4"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.2800.2.2",
            oids=["5"],
        ),
    ],
    parse_function=parse_cbl_airlaser,
)


check_plugin_cbl_airlaser_status = CheckPlugin(
    name="cbl_airlaser_status",
    service_name="CBL Airlaser Status",
    sections=["cbl_airlaser"],
    discovery_function=inventory_cbl_airlaser,
    check_function=check_cbl_airlaser_status,
)


check_plugin_cbl_airlaser_hardware = CheckPlugin(
    name="cbl_airlaser_hardware",
    service_name="CBL Airlaser Hardware",
    sections=["cbl_airlaser"],
    discovery_function=inventory_cbl_airlaser,
    check_function=check_cbl_airlaser_hw,
    check_default_parameters={},
)
