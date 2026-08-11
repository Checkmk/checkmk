#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""
Define concrete implementations for our repositories.

Our application should depend only interfaces as arguments, but receive a concrete implementation
when instantiated.
"""

import datetime as dt
from collections.abc import Mapping, Sequence
from pathlib import PurePosixPath

from cmk.ccc.hostaddress import HostName
from cmk.ccc.site import SiteId
from cmk.livestatus_client import (
    LivestatusClient,
    MultiSiteConnection,
    ScheduleForcedHostCheck,
)
from cmk.livestatus_client.expressions import NothingExpression, Or, QueryExpression
from cmk.livestatus_client.queries import detailed_connection, Query
from cmk.livestatus_client.tables import Hosts

from ._exceptions import HostNotFoundError
from ._models import (
    Host,
    HostFilter,
    HostLabelValue,
    HostOverview,
    HostSort,
    HostSortColumn,
    HostState,
    RescheduleTarget,
    ServiceCounts,
)
from ._sorting import host_sorter


class LiveStatusHostRepository:
    def __init__(self, *, connection: MultiSiteConnection) -> None:
        self._connection = connection

    def fetch(
        self,
        *,
        limit: int | None,
        query: str,
        sorters: Sequence[HostSort],
        filters: HostFilter,
    ) -> Sequence[Host]:
        query_ = _sanitize_query(query)
        extra_headers = [
            *filters.splitlines(),
            _build_primary_sort(sorters),
        ]
        if limit is not None:
            extra_headers.append(f"Limit: {limit}")
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
                Hosts.last_check,
                Hosts.last_state_change,
                Hosts.filename,
            ],
            _build_query_filter(query_),
            extra_headers=extra_headers,
        )

        with detailed_connection(self._connection) as conn:
            return sorted(
                [
                    Host(
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
                        last_check=dt.datetime.fromtimestamp(row["last_check"], tz=dt.UTC),
                        last_state_change=dt.datetime.fromtimestamp(
                            row["last_state_change"], tz=dt.UTC
                        ),
                        folder=_wato_folder_from_filename(row["filename"]),
                    )
                    for row in q.iterate(conn)
                ],
                key=host_sorter(sorters),
            )

    def get_overview(self, *, hostname: str, site_id: str) -> HostOverview:
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
                Hosts.last_check,
                Hosts.last_state_change,
                Hosts.contact_groups,
                Hosts.tags,
                Hosts.labels,
                Hosts.label_sources,
                Hosts.custom_variables,
                Hosts.filename,
            ],
            Hosts.name == hostname,
        )
        try:
            row = q.fetchone(self._connection, True, only_site=SiteId(site_id))
        except ValueError:
            raise HostNotFoundError(f"Host {hostname!r} not found on site {site_id!r}") from None
        return HostOverview(
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
            last_check=dt.datetime.fromtimestamp(row["last_check"], tz=dt.UTC),
            last_state_change=dt.datetime.fromtimestamp(row["last_state_change"], tz=dt.UTC),
            customer=row["custom_variables"].get("CUSTOMER"),
            folder=_wato_folder_from_filename(row["filename"]),
            contact_groups=list(row["contact_groups"]),
            tags=dict(row["tags"]),
            labels={
                key: HostLabelValue(value=value, source=row["label_sources"][key])
                for key, value in row["labels"].items()
            },
        )

    def count_total(self) -> int:
        # Counted via ``Stats`` on the hosts table rather than the global ``status.num_hosts``
        # counter so the ``AuthUser`` filter applies: a user without "see all" counts only the hosts
        # they may see, while an unrestricted user still counts every host.
        return self._count_hosts()

    def count_matched(self, *, query: str, filters: HostFilter) -> int:
        # A filtered total can't be read from the ``status`` table, so the matches are counted
        # server-side via ``Stats`` instead of transferring and counting every matching row. The
        # ``Query`` class can't emit ``Stats`` headers yet, so the filter is assembled by hand.
        query_filter = (
            ": ".join(line) for line in _build_query_filter(_sanitize_query(query)).render()
        )
        return self._count_hosts(extra_lines=[*query_filter, *filters.splitlines()])

    def _count_hosts(self, *, extra_lines: Sequence[str] = ()) -> int:
        # A ``Stats`` count on the hosts table. Runs under the connection's ``AuthUser`` filter, so a
        # user without "see all" counts only the hosts they may see. The count is the trailing column
        # of each returned row; summing across rows adds up the per-site counts. A raw ``Stats`` query
        # returns untyped (string) columns, hence the explicit ``int`` conversion.
        stats_query = "\n".join([f"GET {Hosts.__tablename__}", "Stats: state >= 0", *extra_lines])
        return sum(int(row[-1]) for row in self._connection.query(stats_query))


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


def _wato_folder_from_filename(filename: str) -> str:
    path = PurePosixPath(filename)
    if path.name != "hosts.mk" or path.parts[:2] != ("/", "wato"):
        # Not managed via Setup, e.g. added directly to the monitoring core.
        return ""
    folder = path.relative_to("/wato").parent
    return "/" if folder == PurePosixPath(".") else f"/{folder}"


def _sanitize_query(q: str) -> str:
    # TODO: decide on how we want to handle invalid regex? This will likely require coordinating
    # with frontend implementation to pass down errors to the response.
    return q.replace("*", ".*")


def _build_query_filter(query: str) -> QueryExpression:
    if not query:
        return NothingExpression()

    return Or(
        Hosts.name.contains(query, ignore_case=True),
        Hosts.alias.contains(query, ignore_case=True),
        Hosts.address.contains(query, ignore_case=True),
    )


_LIVESTATUS_COLUMN_OVERRIDES: Mapping[HostSortColumn, str] = {
    HostSortColumn.FOLDER: "filename",
}

# "site" is synthesized client-side by the multisite connection layer while merging rows from
# each site (see ``detailed_connection``'s ``prepend_site``); it isn't a real column on any single
# site's Livestatus core. Sending it in an ``OrderBy`` header makes every site reject the query, so
# it must never reach ``_LIVESTATUS_COLUMN_OVERRIDES``/the raw header below. The correct sort order
# is still fully applied afterwards in Python by ``host_sorter()``.
_VIRTUAL_SORT_COLUMNS = frozenset({HostSortColumn.SITE_ID})


def _build_primary_sort(sorters: Sequence[HostSort]) -> str:
    if not sorters or sorters[0].column in _VIRTUAL_SORT_COLUMNS:
        return "OrderBy: name asc"

    primary = sorters[0]
    column = _LIVESTATUS_COLUMN_OVERRIDES.get(primary.column, primary.column.value)
    natural_sort_flag = " natural" if primary.column.natural_sort else ""

    return f"OrderBy: {column} {primary.direction}{natural_sort_flag}"
