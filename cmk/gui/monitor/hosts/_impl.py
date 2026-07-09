#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""
Define concrete implementations for our repositories.

Our application should depend only interfaces as arguments, but receive a concrete implementation
when instantiated.
"""

from collections.abc import Sequence

from cmk.ccc.hostaddress import HostName
from cmk.ccc.site import SiteId
from cmk.livestatus_client import (
    LivestatusClient,
    MultiSiteConnection,
    ScheduleForcedHostCheck,
)
from cmk.livestatus_client.expressions import NothingExpression, Or, QueryExpression
from cmk.livestatus_client.queries import detailed_connection, Query
from cmk.livestatus_client.tables import Hosts, Status

from ._models import Host, HostFilter, HostSort, HostState, RescheduleTarget, ServiceCounts
from ._sorting import host_sorter


class LiveStatusHostRepository:
    def __init__(self, *, connection: MultiSiteConnection) -> None:
        self._connection = connection

    def fetch(
        self,
        *,
        limit: int,
        query: str,
        sorters: Sequence[HostSort],
        filters: HostFilter,
    ) -> Sequence[Host]:
        query_ = _sanitize_query(query)
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
            ],
            _build_query_filter(query_),
            extra_headers=[
                *filters.splitlines(),
                _build_primary_sort(sorters),
                f"Limit: {limit}",
            ],
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
                    )
                    for row in q.iterate(conn)
                ],
                key=host_sorter(sorters),
            )

    def count_total(self) -> int:
        q = Query([Status.num_hosts])
        with detailed_connection(self._connection) as conn:
            return sum(row["num_hosts"] for row in q.iterate(conn))

    def count_matched(self, *, query: str, filters: HostFilter) -> int:
        # A filtered total can't be read from the ``status`` table. Count the matches server-side
        # via ``Stats`` instead of transferring and counting every matching row. The ``Query`` class
        # can't emit ``Stats`` headers yet, so the query is assembled by hand from the shared filter.
        # The ``Stats`` count is the trailing column of each returned row; summing it across rows
        # adds up the per-site counts.
        query_ = _sanitize_query(query)
        query_filter = (": ".join(line) for line in _build_query_filter(query_).render())
        stats_query = "\n".join(
            [
                f"GET {Hosts.__tablename__}",
                "Stats: state >= 0",
                *query_filter,
                *filters.splitlines(),
            ]
        )
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


def _build_primary_sort(sorters: Sequence[HostSort]) -> str:
    # NOTE (2.5.0 backport): master appends " natural" for natural-sort columns, but the
    # 2.5.0 Livestatus core only understands `OrderBy: COLUMN [asc|desc]` and fails the
    # whole query on the extra token. Rows are re-sorted naturally in Python anyway
    # (host_sorter in _sorting.py); only the page cutoff beyond `Limit:` differs from master.
    condition = f"{sorters[0].column} {sorters[0].direction}" if sorters else "name asc"
    return f"OrderBy: {condition}"
