#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

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

from collections.abc import Mapping, Sequence
from typing import Any

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    SNMPSection,
    SNMPTree,
    startswith,
    State,
    StringTable,
)

Section = Mapping[str, Any]


severity_to_states = {
    "0": ("info", State.OK),
    "1": ("warning", State.WARN),
    "2": ("minor", State.WARN),
    "3": ("major", State.CRIT),
    "4": ("critical", State.CRIT),
    "5": ("cleared", State.UNKNOWN),
    "6": ("acknowledged", State.UNKNOWN),
    "7": ("unacknowledged", State.UNKNOWN),
    "8": ("indeterminate", State.UNKNOWN),
}


def parse_silverpeak(string_table: Sequence[StringTable]) -> Section | None:
    alarm_count, alarms = string_table
    if not alarm_count:
        return None

    parsed: dict[str, Any] = {}

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
                    "state": severity_to_states.get(sever, ("unknown", State.UNKNOWN))[1],
                    "severity_as_text": severity_to_states.get(sever, (f"unkown[{sever}]",))[0],
                    "descr": descr,
                    "source": source,
                }
            )

    return parsed


snmp_section_silverpeak_VX6000 = SNMPSection(
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
)


def discover_silverpeak_VX6000(section: Section) -> DiscoveryResult:
    if section:
        yield Service()


def check_silverpeak(section: Section) -> CheckResult:
    alarm_cnt = section.get("alarm_count", 0)
    if alarm_cnt == 0:
        yield Result(state=State.OK, summary="No active alarms.")
        return

    alarms = section["alarms"]

    cnt_ok = len([alarm for alarm in alarms if alarm["state"] == State.OK])
    cnt_warn = len([alarm for alarm in alarms if alarm["state"] == State.WARN])
    cnt_crit = len([alarm for alarm in alarms if alarm["state"] == State.CRIT])
    cnt_unkn = len([alarm for alarm in alarms if alarm["state"] == State.UNKNOWN])

    yield Result(
        state=State.OK,
        summary=f"{alarm_cnt} active alarms. OK: {cnt_ok}, WARN: {cnt_warn}, CRIT: {cnt_crit}, UNKNOWN: {cnt_unkn}",
    )

    for elem in alarms:
        yield Result(
            state=elem["state"],
            summary="Alarm: {}, Alarm-Source: {}, Severity: {}".format(
                elem["descr"],
                elem["source"],
                elem["severity_as_text"],
            ),
        )


check_plugin_silverpeak_VX6000 = CheckPlugin(
    name="silverpeak_VX6000",
    service_name="Alarms",
    discovery_function=discover_silverpeak_VX6000,
    check_function=check_silverpeak,
)
