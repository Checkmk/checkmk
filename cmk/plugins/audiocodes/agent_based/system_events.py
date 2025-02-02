#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    render,
    Result,
    Service,
    SNMPSection,
    SNMPTree,
    State,
    StringTable,
)

from .lib import DETECT_AUDIOCODES

_READABLE_SEVERITY = {
    "0": "cleared",
    "1": "indeterminate",
    "2": "warning",
    "3": "minor",
    "4": "major",
    "5": "critical",
}


@dataclass(frozen=True)
class ActiveAlarm:
    sequence_number: int
    sysuptime: int
    date_and_time: datetime.datetime
    name: str
    description: str
    source: str
    severity_readable: str


@dataclass(frozen=True)
class Section:
    alarms: Sequence[ActiveAlarm]
    archived_alarm_history_sequence_number: int


def _parse_date_and_time(octet_string: str) -> datetime.datetime:
    components = octet_string.split()

    return datetime.datetime(
        year=int(components[0], 16) * 256 + int(components[1], 16),
        month=int(components[2], 16),
        day=int(components[3], 16),
        hour=int(components[4], 16),
        minute=int(components[5], 16),
        second=int(components[6], 16),
        microsecond=int(components[7], 16) * 100000,
    )


def parse_audiocodes_system_events(string_table: Sequence[StringTable]) -> Section | None:
    return (
        Section(
            alarms=[
                ActiveAlarm(
                    sequence_number=int(alarm[0]),
                    sysuptime=int(alarm[1]),
                    date_and_time=_parse_date_and_time(alarm[2]),
                    name=alarm[3],
                    description=alarm[4],
                    source=alarm[5],
                    severity_readable=_READABLE_SEVERITY[alarm[6]],
                )
                for alarm in string_table[0]
            ],
            archived_alarm_history_sequence_number=int(len(string_table[1])),
        )
        if string_table
        else None
    )


snmp_section_audiocodes_system_events = SNMPSection(
    name="audiocodes_system_events",
    detect=DETECT_AUDIOCODES,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.5003.11.1.1.1.1",
            oids=[
                "1",  # AcAlarm::acActiveAlarmSequenceNumber
                "2",  # AcAlarm::acActiveAlarmSysuptime
                "4",  # AcAlarm::acActiveAlarmDateAndTime
                "5",  # AcAlarm::acActiveAlarmName
                "6",  # AcAlarm::acActiveAlarmTextualDescription
                "7",  # AcAlarm::acActiveAlarmSource
                "8",  # AcAlarm::acActiveAlarmSeverity
            ],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.5003.11.1.2.1.1",
            oids=[
                "1",  # AcAlarm::acAlarmHistorySequenceNumber
            ],
        ),
    ],
    parse_function=parse_audiocodes_system_events,
)


def discover_audiocodes_system_events(section: Section | None) -> DiscoveryResult:
    if section is None:
        return
    yield Service()


def check_audiocodes_system_events(
    params: Mapping[str, Mapping[str, int]], section: Section | None
) -> CheckResult:
    if section is None:
        return

    severity_state_mapping = params["severity_state_mapping"]
    number_of_critical_alarms = 0
    number_of_warning_alarms = 0
    results: list[Result] = []

    for alarm in section.alarms:
        alarm_state = State(severity_state_mapping[alarm.severity_readable])

        if alarm_state == State.CRIT:
            number_of_critical_alarms += 1
        elif alarm_state == State.WARN:
            number_of_warning_alarms += 1
        results.append(
            Result(
                state=alarm_state,
                notice=(
                    f"Alarm #{alarm.sequence_number}: "
                    f"Name: {alarm.name}, "
                    f"Severity: {alarm.severity_readable}, "
                    f"Sysuptime: {render.timespan(alarm.sysuptime)}, "
                    f"Date and Time: {alarm.date_and_time}, "
                    f"Description: {alarm.description}, "
                    f"Source: {alarm.source}"
                ),
            )
        )

    yield Result(
        state=State.OK,
        summary=(
            f"Critical alarms: {number_of_critical_alarms}, Warning alarms: {number_of_warning_alarms}"
        ),
    )

    yield Result(
        state=State.OK,
        summary="Archived alarms: %d" % section.archived_alarm_history_sequence_number,
    )

    yield from results


check_plugin_audiocodes_system_events = CheckPlugin(
    name="audiocodes_system_events",
    service_name="AudioCodes System Events",
    discovery_function=discover_audiocodes_system_events,
    check_function=check_audiocodes_system_events,
    check_ruleset_name="audiocodes_system_events",
    check_default_parameters={
        "severity_state_mapping": {
            "cleared": 0,
            "indeterminate": 3,
            "warning": 1,
            "minor": 1,
            "major": 2,
            "critical": 2,
        }
    },
)
