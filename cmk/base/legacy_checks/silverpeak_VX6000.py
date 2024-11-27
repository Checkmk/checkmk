#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
# .1.3.6.1.4.1.23867.3.1.1.1.4.0 4 --> SILVERPEAK-MGMT-MIB::spsActiveAlarmCount.0
# .1.3.6.1.4.1.23867.3.1.1.2.1.1.3.1 4 --> SILVERPEAK-MGMT-MIB::spsActiveAlarmSeverity.1
# .1.3.6.1.4.1.23867.3.1.1.2.1.1.3.2 4 --> SILVERPEAK-MGMT-MIB::spsActiveAlarmSeverity.2
# .1.3.6.1.4.1.23867.3.1.1.2.1.1.3.3 4 --> SILVERPEAK-MGMT-MIB::spsActiveAlarmSeverity.3
# .1.3.6.1.4.1.23867.3.1.1.2.1.1.3.4 4 --> SILVERPEAK-MGMT-MIB::spsActiveAlarmSeverity.4
# .1.3.6.1.4.1.23867.3.1.1.2.1.1.5.1 Tunnel state is Down --> SILVERPEAK-MGMT-MIB::spsActiveAlarmDescr.1
# .1.3.6.1.4.1.23867.3.1.1.2.1.1.5.2 Tunnel state is Down --> SILVERPEAK-MGMT-MIB::spsActiveAlarmDescr.2
# .1.3.6.1.4.1.23867.3.1.1.2.1.1.5.3 Tunnel state is Down --> SILVERPEAK-MGMT-MIB::spsActiveAlarmDescr.3
# .1.3.6.1.4.1.23867.3.1.1.2.1.1.5.4 Tunnel state is Down --> SILVERPEAK-MGMT-MIB::spsActiveAlarmDescr.4
# .1.3.6.1.4.1.23867.3.1.1.2.1.1.6.1 to_sp01-wpg_WAN-WAN --> SILVERPEAK-MGMT-MIB::spsActiveAlarmSource.1
# .1.3.6.1.4.1.23867.3.1.1.2.1.1.6.2 to_sp01-dnd_GLB_Overlay --> SILVERPEAK-MGMT-MIB::spsActiveAlarmSource.2
# .1.3.6.1.4.1.23867.3.1.1.2.1.1.6.3 to_sp01-dnd_WAN-WAN --> SILVERPEAK-MGMT-MIB::spsActiveAlarmSource.3
# .1.3.6.1.4.1.23867.3.1.1.2.1.1.6.4 to_sp01-mad_WAN-WAN --> SILVERPEAK-MGMT-MIB::spsActiveAlarmSource.4

# Taken from SILVERPEAK-TC.txt: translates silverpeak severities to checkmk's OK,WARN,CRIT


# mypy: disable-error-code="var-annotated,index"

from collections.abc import Iterable, Mapping
from typing import Any

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, startswith

check_info = {}

Section = Mapping[str, Any]


severity_to_states = {
    "0": ("info", 0),
    "1": ("warning", 1),
    "2": ("minor", 1),
    "3": ("major", 2),
    "4": ("critical", 2),
    "5": ("cleared", 3),
    "6": ("acknowledged", 3),
    "7": ("unacknowledged", 3),
    "8": ("indeterminate", 3),
}


def parse_silverpeak(string_table):
    alarm_count, alarms = string_table
    if not alarm_count:
        return None

    parsed = {}

    # We currently do not know if any (alarm) OIDs will be delivered in case no alarm is active.
    # Therefore acquire the alarm count in any case.
    if alarm_count[0][0]:
        parsed.setdefault("alarm_count", int(alarm_count[0][0]))

    for line in alarms:
        sever = line[0]
        descr = line[1]
        source = line[2]

        if source:
            parsed.setdefault("alarms", [])
            parsed["alarms"].append(
                {
                    "state": severity_to_states.get(sever, 3)[1],
                    "severity_as_text": severity_to_states.get(sever, "unkown[%s]" % sever)[0],
                    "descr": descr,
                    "source": source,
                }
            )

    return parsed


def discover_silverpeak_VX6000(section: Section) -> Iterable[tuple[None, dict]]:
    if section:
        yield None, {}


def check_silverpeak(_item, _params, parsed):
    alarm_cnt = parsed.get("alarm_count", 0)
    if alarm_cnt == 0:
        yield 0, "No active alarms."
        return

    alarms = parsed["alarms"]

    cnt_ok = len([alarm for alarm in alarms if alarm["state"] == 0])
    cnt_warn = len([alarm for alarm in alarms if alarm["state"] == 1])
    cnt_crit = len([alarm for alarm in alarms if alarm["state"] == 2])
    cnt_unkn = len([alarm for alarm in alarms if alarm["state"] == 3])

    yield (
        0,
        f"{alarm_cnt} active alarms. OK: {cnt_ok}, WARN: {cnt_warn}, CRIT: {cnt_crit}, UNKNOWN: {cnt_unkn}",
    )

    for elem in alarms:
        yield (
            elem["state"],
            "\nAlarm: {}, Alarm-Source: {}, Severity: {}".format(
                elem["descr"],
                elem["source"],
                elem["severity_as_text"],
            ),
        )


check_info["silverpeak_VX6000"] = LegacyCheckDefinition(
    name="silverpeak_VX6000",
    detect=startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.23867"),
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.23867.3.1.1.1",
            oids=["4"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.23867.3.1.1.2.1.1",
            oids=["3", "5", "6"],
        ),
    ],
    parse_function=parse_silverpeak,
    service_name="Alarms",
    discovery_function=discover_silverpeak_VX6000,
    check_function=check_silverpeak,
)
