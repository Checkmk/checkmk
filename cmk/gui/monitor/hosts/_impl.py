#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""
Define concrete implementations for our repositories.

Our application should depend only interfaces as arguments, but receive a concrete implementation
when instantiated.
"""

from collections.abc import Callable, Mapping, Sequence, Set

from cmk.ccc.hostaddress import HostName
from cmk.ccc.site import SiteId
from cmk.gui.config import active_config
from cmk.livestatus_client import (
    LivestatusClient,
    MultiSiteConnection,
    ScheduleForcedHostCheck,
)
from cmk.livestatus_client.expressions import And, NothingExpression, Or, QueryExpression
from cmk.livestatus_client.queries import detailed_connection, Query
from cmk.livestatus_client.tables import Hosts, Log
from cmk.livestatus_client.types import Column

from ._exceptions import HostNotFoundError
from ._folder import folder_files_matching, folder_title, MonitorFolders
from ._models import (
    Event,
    EventClass,
    Host,
    HostFilter,
    HostLabelValue,
    HostOptionalField,
    HostSort,
    HostSortColumn,
    HostState,
    RescheduleTarget,
    ServiceCounts,
    UnixTimestamp,
)
from ._sorting import host_sorter


class LiveStatusHostRepository:
    def __init__(
        self,
        *,
        connection: MultiSiteConnection,
        folders: MonitorFolders | None = None,
    ) -> None:
        self._connection = connection
        # A folder is shown and searched by its Setup title, which Livestatus does not have. A
        # caller reading no folder needs none, hence the default that knows no titles.
        self._folders = folders if folders is not None else MonitorFolders()

    def host_exists(self, hostname: str) -> bool:
        q = Query([Hosts.name], Hosts.name == hostname, extra_headers=["Limit: 1"])
        return q.first(self._connection) is not None

    def fetch(
        self,
        *,
        limit: int | None,
        query: str,
        sorters: Sequence[HostSort],
        filters: HostFilter,
        fields: Set[HostOptionalField],
    ) -> Sequence[Host]:
        query_ = _sanitize_query(query)
        extra_headers = [
            *filters.splitlines(),
            _build_primary_sort(sorters),
        ]
        if limit is not None:
            extra_headers.append(f"Limit: {limit}")
        wanted = _columns_to_read(fields, sorters)
        q = Query(
            [
                Hosts.name,
                Hosts.state,
                Hosts.acknowledged,
                Hosts.scheduled_downtime_depth,
                Hosts.is_flapping,
                Hosts.staleness,
                *(
                    column
                    for field, columns in _OPTIONAL_COLUMNS.items()
                    if field in wanted
                    for column in columns
                ),
            ],
            _build_query_filter(query_, fields, self._folders),
            extra_headers=extra_headers,
        )

        with detailed_connection(self._connection) as conn:
            return sorted(
                [
                    Host(
                        name=row["name"],
                        alias=row.get("alias"),
                        address=row.get("address"),
                        state=HostState(row["state"]),
                        site_id=row["site"],
                        service_counts=_service_counts(row),
                        acknowledged=bool(row["acknowledged"]),
                        in_downtime=row["scheduled_downtime_depth"] > 0,
                        is_flapping=bool(row["is_flapping"]),
                        stale=row["staleness"] >= active_config.staleness_threshold,
                        last_check=_timestamp(row.get("last_check")),
                        last_state_change=_timestamp(row.get("last_state_change")),
                        folder=(
                            None
                            if (filename := row.get("filename")) is None
                            else folder_title(filename, self._folders.title_of)
                        ),
                        labels=(
                            HostLabelValue.by_label(row["labels"], row["label_sources"])
                            if "labels" in row
                            else None
                        ),
                        tags=dict(row["tags"]) if "tags" in row else None,
                        contacts=list(row["contacts"]) if "contacts" in row else None,
                        contact_groups=(
                            list(row["contact_groups"]) if "contact_groups" in row else None
                        ),
                    )
                    for row in q.iterate(conn)
                ],
                key=host_sorter(sorters),
            )

    def get_overview(self, *, hostname: str, site_id: str) -> Host:
        q = Query(
            [
                Hosts.name,
                Hosts.alias,
                Hosts.address,
                Hosts.state,
                Hosts.num_services,
                Hosts.num_services_ok,
                Hosts.num_services_warn,
                Hosts.num_services_crit,
                Hosts.num_services_unknown,
                Hosts.num_services_pending,
                Hosts.acknowledged,
                Hosts.scheduled_downtime_depth,
                Hosts.is_flapping,
                Hosts.staleness,
                Hosts.last_check,
                Hosts.last_state_change,
                Hosts.contact_groups,
                Hosts.tags,
                Hosts.labels,
                Hosts.label_sources,
                Hosts.filename,
            ],
            Hosts.name == hostname,
        )
        try:
            row = q.fetchone(self._connection, True, only_site=SiteId(site_id))
        except ValueError:
            raise HostNotFoundError(f"Host {hostname!r} not found on site {site_id!r}") from None
        return Host(
            name=row["name"],
            alias=row["alias"],
            address=row["address"],
            state=HostState(row["state"]),
            site_id=row["site"],
            service_counts=ServiceCounts(
                total=row["num_services"],
                ok=row["num_services_ok"],
                warn=row["num_services_warn"],
                crit=row["num_services_crit"],
                unknown=row["num_services_unknown"],
                pending=row["num_services_pending"],
            ),
            acknowledged=bool(row["acknowledged"]),
            in_downtime=row["scheduled_downtime_depth"] > 0,
            is_flapping=bool(row["is_flapping"]),
            stale=row["staleness"] >= active_config.staleness_threshold,
            last_check=int(row["last_check"]),
            last_state_change=int(row["last_state_change"]),
            folder=folder_title(row["filename"], self._folders.title_of),
            contact_groups=list(row["contact_groups"]),
            tags=dict(row["tags"]),
            # The overview does not expose contacts, so its query does not read them.
            contacts=[],
            labels=HostLabelValue.by_label(row["labels"], row["label_sources"]),
        )

    def count_total(self) -> int:
        # Counted via ``Stats`` on the hosts table rather than the global ``status.num_hosts``
        # counter so the ``AuthUser`` filter applies: a user without "see all" counts only the hosts
        # they may see, while an unrestricted user still counts every host.
        return self._count_hosts()

    def count_matched(
        self, *, query: str, filters: HostFilter, fields: Set[HostOptionalField]
    ) -> int:
        # A filtered total can't be read from the ``status`` table, so the matches are counted
        # server-side via ``Stats`` instead of transferring and counting every matching row. The
        # ``Query`` class can't emit ``Stats`` headers yet, so the filter is assembled by hand.
        query_filter = (
            ": ".join(line)
            for line in _build_query_filter(_sanitize_query(query), fields, self._folders).render()
        )
        return self._count_hosts(extra_lines=[*query_filter, *filters.splitlines()])

    def _count_hosts(self, *, extra_lines: Sequence[str] = ()) -> int:
        # A ``Stats`` count on the hosts table. Runs under the connection's ``AuthUser`` filter, so a
        # user without "see all" counts only the hosts they may see. The count is the trailing column
        # of each returned row; summing across rows adds up the per-site counts. A raw ``Stats`` query
        # returns untyped (string) columns, hence the explicit ``int`` conversion.
        stats_query = "\n".join([f"GET {Hosts.__tablename__}", "Stats: state >= 0", *extra_lines])
        return sum(int(row[-1]) for row in self._connection.query(stats_query))


class LiveStatusEventRepository:
    def __init__(self, *, connection: MultiSiteConnection) -> None:
        self._connection = connection

    def fetch(
        self,
        *,
        hostname: str,
        service_name: str | None,
        since: UnixTimestamp,
        limit: int,
    ) -> Sequence[Event]:
        q = Query(
            [
                Log.time,
                Log.lineno,
                Log.type,
                Log.state,
                Log.state_type,
                Log.state_info,
                Log.command_name,
                Log.plugin_output,
                Log.service_description,
            ],
            _build_event_filter(hostname=hostname, service_name=service_name, since=since),
            extra_headers=["OrderBy: time desc", f"Limit: {limit}"],
        )
        return sorted(
            [
                Event(
                    time=int(row["time"]),
                    lineno=int(row["lineno"]),
                    type=row["type"],
                    state=int(row["state"]),
                    state_type=row["state_type"],
                    state_info=row["state_info"],
                    command_name=row["command_name"],
                    plugin_output=row["plugin_output"],
                    service_name=row["service_description"] or None,
                )
                for row in q.iterate(self._connection)
            ],
            key=lambda event: event.recency,
            reverse=True,
        )


class LiveStatusHostActions:
    def __init__(self, *, connection: MultiSiteConnection) -> None:
        self._connection = connection

    def reschedule(self, targets: Sequence[RescheduleTarget]) -> None:
        client = LivestatusClient(self._connection)
        for target in targets:
            client.command(
                ScheduleForcedHostCheck(
                    host_name=HostName(target.host_name),
                    check_time=target.check_time,
                ),
                SiteId(target.site_id),
            )


def _sanitize_query(q: str) -> str:
    # TODO: decide on how we want to handle invalid regex? This will likely require coordinating
    # with frontend implementation to pass down errors to the response.
    return q.replace("*", ".*")


_SEARCHED_FIELDS: Mapping[HostOptionalField, Callable[[str], QueryExpression]] = {
    HostOptionalField.ALIAS: lambda query: Hosts.alias.contains(query, ignore_case=True),
    HostOptionalField.ADDRESS: lambda query: Hosts.address.contains(query, ignore_case=True),
}


def _build_query_filter(
    query: str, fields: Set[HostOptionalField], folders: MonitorFolders
) -> QueryExpression:
    if not query:
        return NothingExpression()

    searched = [build(query) for field, build in _SEARCHED_FIELDS.items() if field in fields]
    if HostOptionalField.FOLDER in fields:
        # The folder is searched by the title Setup shows, which Livestatus has never heard of, so
        # the folders carrying the query are resolved first and asked for by file.
        searched.extend(
            Hosts.filename.equals(file) for file in folder_files_matching(query, folders.titles())
        )

    return Or(Hosts.name.contains(query, ignore_case=True), *searched)


# Sorting by folder means sorting by the title Setup gives it, which Livestatus cannot do: it only
# has the file. So the header below merely bounds which rows a ``Limit:`` keeps, and the order the
# user sees is the natural sort ``host_sorter()`` applies afterwards. Ordering by file is no longer
# even close to ordering by title - "Data center Munich" lives in ``dc_muc`` - so a listing longer
# than the limit, sorted by folder, shows the right rows in the right order only within the window
# the limit kept.
_LIVESTATUS_COLUMN_OVERRIDES: Mapping[HostSortColumn, str] = {
    HostSortColumn.FOLDER: "filename",
}

# "site" is synthesized client-side by the multisite connection layer while merging rows from
# each site (see ``detailed_connection``'s ``prepend_site``); it isn't a real column on any single
# site's Livestatus core. Sending it in an ``OrderBy`` header makes every site reject the query, so
# it must never reach ``_LIVESTATUS_COLUMN_OVERRIDES``/the raw header below. The correct sort order
# is still fully applied afterwards in Python by ``host_sorter()``.
_VIRTUAL_SORT_COLUMNS = frozenset({HostSortColumn.SITE_ID})


# Everything beyond the columns every host row needs is read only when a caller asks for it,
# either through `fields` or by sorting on it - the list is sorted in Python, so a sort column
# has to be read even when the response omits it.
_OPTIONAL_COLUMNS: Mapping[HostOptionalField, tuple[Column, ...]] = {
    HostOptionalField.ALIAS: (Hosts.alias,),
    HostOptionalField.ADDRESS: (Hosts.address,),
    HostOptionalField.NUM_SERVICES: (Hosts.num_services,),
    HostOptionalField.NUM_SERVICES_OK: (Hosts.num_services_ok,),
    HostOptionalField.NUM_SERVICES_WARN: (Hosts.num_services_warn,),
    HostOptionalField.NUM_SERVICES_CRIT: (Hosts.num_services_crit,),
    HostOptionalField.NUM_SERVICES_UNKNOWN: (Hosts.num_services_unknown,),
    HostOptionalField.NUM_SERVICES_PENDING: (Hosts.num_services_pending,),
    HostOptionalField.FOLDER: (Hosts.filename,),
    HostOptionalField.LAST_CHECK: (Hosts.last_check,),
    HostOptionalField.LAST_STATE_CHANGE: (Hosts.last_state_change,),
    HostOptionalField.LABELS: (Hosts.labels, Hosts.label_sources),
    HostOptionalField.TAGS: (Hosts.tags,),
    HostOptionalField.CONTACTS: (Hosts.contacts,),
    HostOptionalField.CONTACT_GROUPS: (Hosts.contact_groups,),
}

_SORT_COLUMN_FIELDS: Mapping[HostSortColumn, HostOptionalField] = {
    HostSortColumn.ALIAS: HostOptionalField.ALIAS,
    HostSortColumn.ADDRESS: HostOptionalField.ADDRESS,
    HostSortColumn.NUM_SERVICES: HostOptionalField.NUM_SERVICES,
    HostSortColumn.NUM_SERVICES_OK: HostOptionalField.NUM_SERVICES_OK,
    HostSortColumn.NUM_SERVICES_WARN: HostOptionalField.NUM_SERVICES_WARN,
    HostSortColumn.NUM_SERVICES_CRIT: HostOptionalField.NUM_SERVICES_CRIT,
    HostSortColumn.NUM_SERVICES_UNKNOWN: HostOptionalField.NUM_SERVICES_UNKNOWN,
    HostSortColumn.NUM_SERVICES_PENDING: HostOptionalField.NUM_SERVICES_PENDING,
    HostSortColumn.FOLDER: HostOptionalField.FOLDER,
    HostSortColumn.LAST_CHECK: HostOptionalField.LAST_CHECK,
    HostSortColumn.LAST_STATE_CHANGE: HostOptionalField.LAST_STATE_CHANGE,
}


def _columns_to_read(
    fields: Set[HostOptionalField], sorters: Sequence[HostSort]
) -> Set[HostOptionalField]:
    return set(fields) | {
        field for sorter in sorters if (field := _SORT_COLUMN_FIELDS.get(sorter.column)) is not None
    }


def _timestamp(value: float | None) -> UnixTimestamp | None:
    return None if value is None else int(value)


def _service_counts(row: Mapping[str, object]) -> ServiceCounts | None:
    """The counts are read as a block, so one missing column means none were asked for."""
    if "num_services" not in row:
        return None
    return ServiceCounts(
        total=int(row["num_services"]),  # type: ignore[call-overload]
        ok=int(row["num_services_ok"]),  # type: ignore[call-overload]
        warn=int(row["num_services_warn"]),  # type: ignore[call-overload]
        crit=int(row["num_services_crit"]),  # type: ignore[call-overload]
        unknown=int(row["num_services_unknown"]),  # type: ignore[call-overload]
        pending=int(row["num_services_pending"]),  # type: ignore[call-overload]
    )


def _build_primary_sort(sorters: Sequence[HostSort]) -> str:
    if not sorters or sorters[0].column in _VIRTUAL_SORT_COLUMNS:
        return "OrderBy: name asc"

    primary = sorters[0]
    column = _LIVESTATUS_COLUMN_OVERRIDES.get(primary.column, primary.column.value)
    natural_sort_flag = " natural" if primary.column.natural_sort else ""

    return f"OrderBy: {column} {primary.direction}{natural_sort_flag}"


def _build_event_filter(
    *, hostname: str, service_name: str | None, since: UnixTimestamp
) -> QueryExpression:
    conditions = [
        Log.time >= since,
        Log.host_name == hostname,
        Or(*(Log.class_ == event_class.value for event_class in EventClass)),
    ]
    if service_name is not None:
        conditions.append(Log.service_description == service_name)
    return And(*conditions)
