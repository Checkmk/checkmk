#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from time import time
from typing import get_args, Literal

from livestatus import lqencode, MultiSiteConnection, OnlySites

from cmk.ccc.site import SiteId

from cmk.utils.livestatus_helpers.expressions import Or, QueryExpression
from cmk.utils.livestatus_helpers.queries import Query
from cmk.utils.livestatus_helpers.tables.eventconsoleevents import Eventconsoleevents
from cmk.utils.statename import core_state_names

import cmk.ec.export as ec  # pylint: disable=cmk-module-layer-violation

from cmk.gui.logged_in import user


class EventNotFoundError(ValueError):
    pass


state_names = [v.lower() for v in core_state_names().values() if v != "NODATA"]

states_ints_reversed = {v.lower(): k for k, v in core_state_names().items() if v != "NODATA"}

ServiceLevelType = Literal[
    "no_service_level",
    "silver",
    "gold",
    "platinum",
]


@dataclass
class ECEvent:
    site: str
    event_id: int
    event_state: int
    event_sl: int
    event_host: str
    event_rule_id: str
    event_application: str
    event_comment: str
    event_contact: str
    event_ipaddress: str
    event_facility: int
    event_priority: int
    event_phase: str
    event_last: int
    event_first: int
    event_count: int
    event_text: str

    def __iter__(self) -> Iterator:
        """return a dict representation of the ECEvent object to
        send back via the response schema.

        >>> dict(ECEvent("heute", 1, 1, 10, "heute", "rule_id_1", "app1", "", "", "123.12.13.1", 6, 7, "open", 1668007771, 1667403030, 6, "test_text"))
        {'site_id': 'heute', 'state': 'warning', 'service_level': 'silver', 'host': 'heute', 'rule_id': 'rule_id_1', 'application': 'app1', 'comment': '', 'contact': '', 'ipaddress': '123.12.13.1', 'facility': 'lpr', 'priority': 'debug', 'phase': 'open', 'last': 1668007771, 'first': 1667403030, 'count': 6, 'text': 'test_text'}

        """

        for k, v in self.__dict__.items():
            k = k.removeprefix("event_")
            if k == "state":
                yield k, (state_names[v]).lower()
                continue

            if k == "sl":
                yield (
                    "service_level",
                    dict(zip([0, 10, 20, 30], list(get_args(ServiceLevelType))))[v],
                )
                continue

            if k == "priority":
                yield k, ec.SyslogPriority.NAMES.get(v, "unknown")
                continue

            if k == "facility":
                yield k, ec.SyslogFacility.NAMES.get(v, "unknown")

                continue

            if k == "id":
                continue

            if k == "site":
                yield "site_id", v
                continue

            yield k, v


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


def send_command(connection: MultiSiteConnection, cmd: str, site: str) -> None:
    connection.command(f"[{int(time())}] {cmd}", SiteId(site))


def filter_event_table(
    event_id: int | None = None,
    event_ids: list[int] | None = None,
    state: str | None = None,
    application: str | None = None,
    host: str | None = None,
    phase: str | None = None,
    query: QueryExpression | None = None,
) -> Query:
    q = query_event_console().filter(query) if query else query_event_console()

    if event_id is not None:
        q = q.filter(Eventconsoleevents.event_id == event_id)

    if event_ids is not None:
        q = q.filter(Or(*[Eventconsoleevents.event_id == ev_id for ev_id in event_ids]))

    if state is not None:
        q = q.filter(Eventconsoleevents.event_state == states_ints_reversed[state])

    if application is not None:
        q = q.filter(Eventconsoleevents.event_application == application)

    if phase is not None:
        q = q.filter(Eventconsoleevents.event_phase == phase)

    if host is not None:
        q = q.filter(Eventconsoleevents.event_host == host)

    return q


def get_all_events(
    connection: MultiSiteConnection, q: Query, site_id: SiteId | None
) -> dict[int, ECEvent]:
    _site_id: OnlySites = [site_id] if site_id is not None else None
    return {ev["event_id"]: ECEvent(**ev) for ev in q.fetchall(connection, True, _site_id)}


def get_single_event_by_id(
    connection: MultiSiteConnection, event_id: int, site_id: SiteId
) -> ECEvent:
    try:
        ev = ECEvent(**filter_event_table(event_id=event_id).fetchone(connection, True, site_id))
    except ValueError:
        raise EventNotFoundError

    return ev


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
    ack = "1" if new_phase == "ack" else "0"
    sites_with_ids = map_sites_to_ids_from_query(connection, query, site_id)
    for site, event_ids in sites_with_ids.items():
        event_ids_joined = ",".join(event_ids)
        cmd = f"EC_UPDATE;{event_ids_joined};{user.ident};{ack};{lqencode(change_comment)};{lqencode(change_contact)}"
        send_command(connection, cmd, site)
    return sites_with_ids


def change_state(
    connection: MultiSiteConnection,
    state: str,
    query: Query,
    site_id: SiteId | None,
) -> Mapping[str, list[str]]:
    sites_with_ids = map_sites_to_ids_from_query(connection, query, site_id)
    for site, event_ids in sites_with_ids.items():
        event_ids_joined = ",".join(event_ids)
        cmd = f"EC_CHANGESTATE;{event_ids_joined};{user.ident};{states_ints_reversed[state]}"
        send_command(connection, cmd, site)
    return sites_with_ids


def archive_events(
    connection: MultiSiteConnection,
    query: Query,
    site_id: SiteId | None,
) -> None:
    sites_with_ids = map_sites_to_ids_from_query(connection, query, site_id)
    for site, event_ids in sites_with_ids.items():
        event_ids_joined = ",".join(event_ids)
        cmd = f"EC_DELETE;{event_ids_joined};{user.ident}"
        send_command(connection, cmd, site)
