#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping
from typing import Final, Literal

from cmk.livestatus_client.expressions import Or, QueryExpression
from cmk.livestatus_client.queries import Query
from cmk.livestatus_client.tables.eventconsolehistory import Eventconsolehistory

StateNameType = Literal[
    "ok",
    "warning",
    "critical",
    "unknown",
]
STATE_INT_TO_NAME_MAP: Final[Mapping[Literal[0, 1, 2, 3], StateNameType]] = {
    0: "ok",
    1: "warning",
    2: "critical",
    3: "unknown",
}

STATE_NAME_TO_INT_MAP: Final[Mapping[StateNameType, Literal[0, 1, 2, 3]]] = {
    name: num for num, name in STATE_INT_TO_NAME_MAP.items()
}

HistoricalPhaseType = Literal[
    "open",
    "ack",
    "closed",
    "delayed",
    "counting",
]


ServiceLevelType = Literal[
    "no_service_level",
    "silver",
    "gold",
    "platinum",
]
SERVICE_LEVEL_INT_TO_NAME_MAP: Final[Mapping[Literal[0, 10, 20, 30], ServiceLevelType]] = {
    0: "no_service_level",
    10: "silver",
    20: "gold",
    30: "platinum",
}

SyslogFacilityType = Literal[
    "kern",
    "user",
    "mail",
    "daemon",
    "auth",
    "syslog",
    "lpr",
    "news",
    "uucp",
    "cron",
    "authpriv",
    "ftp",
    "ntp",
    "logaudit",
    "logalert",
    "clock",
    "local0",
    "local1",
    "local2",
    "local3",
    "local4",
    "local5",
    "logfile",
    "local6",
    "local7",
    "snmptrap",
]
SYSLOG_FACILITY_INT_TO_NAME_MAP: Final[
    Mapping[
        Literal[
            0,
            1,
            2,
            3,
            4,
            5,
            6,
            7,
            8,
            9,
            10,
            11,
            12,
            13,
            14,
            15,
            16,
            17,
            18,
            19,
            20,
            21,
            22,
            23,
            30,
            31,
        ],
        SyslogFacilityType,
    ]
] = {
    0: "kern",
    1: "user",
    2: "mail",
    3: "daemon",
    4: "auth",
    5: "syslog",
    6: "lpr",
    7: "news",
    8: "uucp",
    9: "cron",
    10: "authpriv",
    11: "ftp",
    12: "ntp",
    13: "logaudit",
    14: "logalert",
    15: "clock",
    16: "local0",
    17: "local1",
    18: "local2",
    19: "local3",
    20: "local4",
    21: "local5",
    22: "local6",
    23: "local7",
    30: "logfile",
    31: "snmptrap",
}


SyslogPriorityType = Literal[
    "emerg",
    "alert",
    "crit",
    "err",
    "warning",
    "notice",
    "info",
    "debug",
]

SYSLOG_PRIORITY_INT_TO_NAME_MAP: Final[
    Mapping[Literal[0, 1, 2, 3, 4, 5, 6, 7], SyslogPriorityType]
] = {
    0: "emerg",
    1: "alert",
    2: "crit",
    3: "err",
    4: "warning",
    5: "notice",
    6: "info",
    7: "debug",
}


def query_event_console_history() -> Query:
    return Query(
        [
            Eventconsolehistory.history_time,
            Eventconsolehistory.history_what,
            Eventconsolehistory.event_id,
            Eventconsolehistory.event_state,
            Eventconsolehistory.event_sl,
            Eventconsolehistory.event_host,
            Eventconsolehistory.event_rule_id,
            Eventconsolehistory.event_application,
            Eventconsolehistory.event_comment,
            Eventconsolehistory.event_contact,
            Eventconsolehistory.event_ipaddress,
            Eventconsolehistory.event_facility,
            Eventconsolehistory.event_priority,
            Eventconsolehistory.event_count,
            Eventconsolehistory.event_phase,
            Eventconsolehistory.event_text,
        ]
    )


def filter_historical_events_table(
    event_ids: list[int] | None = None,
    state: StateNameType | None = None,
    application: str | None = None,
    host: str | None = None,
    phase: HistoricalPhaseType | None = None,
    query_expression: QueryExpression | None = None,
) -> Query:
    query = (
        query_event_console_history().filter(query_expression)
        if query_expression
        else query_event_console_history()
    )

    if event_ids is not None:
        query = query.filter(Or(*[Eventconsolehistory.event_id == ev_id for ev_id in event_ids]))

    if state is not None:
        query = query.filter(Eventconsolehistory.event_state == STATE_NAME_TO_INT_MAP[state])

    if application is not None:
        query = query.filter(Eventconsolehistory.event_application == application)

    if phase is not None:
        query = query.filter(Eventconsolehistory.event_phase == phase)

    if host is not None:
        query = query.filter(Eventconsolehistory.event_host == host)

    return query
