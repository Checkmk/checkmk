#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="type-arg"


from collections.abc import Mapping
from typing import Final, Literal

from livestatus import MultiSiteConnection, OnlySites

from cmk.ccc.site import SiteId
from cmk.gui.logged_in import user
from cmk.livestatus_client import ECChangeState, ECDelete, ECUpdate, LivestatusClient
from cmk.livestatus_client.expressions import Or, QueryExpression
from cmk.livestatus_client.queries import Query
from cmk.livestatus_client.tables.eventconsoleevents import Eventconsoleevents
from cmk.livestatus_client.tables.eventconsolehistory import Eventconsolehistory

ServiceStateType = Literal[
    "ok",
    "warning",
    "critical",
    "unknown",
]
STATE_INT_TO_NAME_MAP: Final[Mapping[Literal[0, 1, 2, 3], ServiceStateType]] = {
    0: "ok",
    1: "warning",
    2: "critical",
    3: "unknown",
}

STATE_NAME_TO_INT_MAP: Final[Mapping[ServiceStateType, Literal[0, 1, 2, 3]]] = {
    name: num for num, name in STATE_INT_TO_NAME_MAP.items()
}

HistoricalPhaseType = Literal[
    "open",
    "ack",
    "closed",
    "delayed",
    "counting",
]

PhaseType = Literal[
    "open",
    "ack",
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


#  _____                 _      ____                      _
# | ____|_   _____ _ __ | |_   / ___|___  _ __  ___  ___ | | ___
# |  _| \ \ / / _ \ '_ \| __| | |   / _ \| '_ \/ __|/ _ \| |/ _ \
# | |___ \ V /  __/ | | | |_  | |__| (_) | | | \__ \ (_) | |  __/
# |_____| \_/ \___|_| |_|\__|  \____\___/|_| |_|___/\___/|_|\___|


def query_event_console() -> Query:
    return Query(
        [
            Eventconsoleevents.event_id,
            Eventconsoleevents.event_state,
            Eventconsoleevents.event_sl,
            Eventconsoleevents.event_host,
            Eventconsoleevents.event_rule_id,
            Eventconsoleevents.event_application,
            Eventconsoleevents.event_comment,
            Eventconsoleevents.event_contact,
            Eventconsoleevents.event_ipaddress,
            Eventconsoleevents.event_facility,
            Eventconsoleevents.event_priority,
            Eventconsoleevents.event_last,
            Eventconsoleevents.event_first,
            Eventconsoleevents.event_count,
            Eventconsoleevents.event_phase,
            Eventconsoleevents.event_text,
        ]
    )


def filter_event_table(
    event_id: int | None = None,
    event_ids: list[int] | None = None,
    state: ServiceStateType | None = None,
    application: str | None = None,
    host: str | None = None,
    phase: PhaseType | None = None,
    query: QueryExpression | None = None,
) -> Query:
    q = query_event_console().filter(query) if query else query_event_console()

    if event_id is not None:
        q = q.filter(Eventconsoleevents.event_id == event_id)

    if event_ids is not None:
        q = q.filter(Or(*[Eventconsoleevents.event_id == ev_id for ev_id in event_ids]))

    if state is not None:
        q = q.filter(Eventconsoleevents.event_state == STATE_NAME_TO_INT_MAP[state])

    if application is not None:
        q = q.filter(Eventconsoleevents.event_application == application)

    if phase is not None:
        q = q.filter(Eventconsoleevents.event_phase == phase)

    if host is not None:
        q = q.filter(Eventconsoleevents.event_host == host)

    return q


def map_sites_to_ids_from_query(
    connection: MultiSiteConnection,
    query: Query,
    site_id: SiteId | None,
) -> Mapping[str, list[str]]:
    _site_id: OnlySites = [site_id] if site_id is not None else None
    sites_with_ids: dict[str, list[str]] = {}
    for row in query.fetchall(connection, True, _site_id):
        event_id_list = sites_with_ids.setdefault(row["site"], [])
        event_id_list.append(str(row["event_id"]))
    return sites_with_ids


def update_and_acknowledge(
    connection: MultiSiteConnection,
    change_comment: str,
    change_contact: str,
    query: Query,
    new_phase: Literal["ack", "open"],
    site_id: SiteId | None,
) -> Mapping[str, list[str]]:
    ack = new_phase == "ack"
    sites_with_ids = map_sites_to_ids_from_query(connection, query, site_id)
    for site, event_ids in sites_with_ids.items():
        ids = tuple(map(int, event_ids))
        LivestatusClient(connection).command(
            ECUpdate(
                event_ids=ids,
                user=user.ident,
                acknowledgement=ack,
                comment=change_comment,
                contact=change_contact,
            ),
            SiteId(site),
        )
    return sites_with_ids


def change_state(
    connection: MultiSiteConnection,
    state: ServiceStateType,
    query: Query,
    site_id: SiteId | None,
) -> Mapping[str, list[str]]:
    sites_with_ids = map_sites_to_ids_from_query(connection, query, site_id)
    for site, event_ids in sites_with_ids.items():
        ids = tuple(map(int, event_ids))
        LivestatusClient(connection).command(
            ECChangeState(event_ids=ids, user=user.ident, state=STATE_NAME_TO_INT_MAP[state]),
            SiteId(site),
        )
    return sites_with_ids


def archive_events(
    connection: MultiSiteConnection,
    query: Query,
    site_id: SiteId | None,
) -> None:
    sites_with_ids = map_sites_to_ids_from_query(connection, query, site_id)
    for site, event_ids in sites_with_ids.items():
        ids = tuple(map(int, event_ids))
        LivestatusClient(connection).command(ECDelete(event_ids=ids, user=user.ident), SiteId(site))


#  _____                 _      ____                      _
# | ____|_   _____ _ __ | |_   / ___|___  _ __  ___  ___ | | ___
# |  _| \ \ / / _ \ '_ \| __| | |   / _ \| '_ \/ __|/ _ \| |/ _ \
# | |___ \ V /  __/ | | | |_  | |__| (_) | | | \__ \ (_) | |  __/
# |_____| \_/ \___|_| |_|\__|  \____\___/|_| |_|___/\___/|_|\___|
#  _   _ _     _
# | | | (_)___| |_ ___  _ __ _   _
# | |_| | / __| __/ _ \| '__| | | |
# |  _  | \__ \ || (_) | |  | |_| |
# |_| |_|_|___/\__\___/|_|   \__, |
#                            |___/


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
    state: ServiceStateType | None = None,
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
