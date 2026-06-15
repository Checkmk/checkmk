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

from cmk.livestatus_client import MultiSiteConnection
from cmk.livestatus_client.expressions import NothingExpression, Or, QueryExpression
from cmk.livestatus_client.queries import detailed_connection, Query
from cmk.livestatus_client.tables import Hosts, Status

from ._models import Host, HostSort, HostState, ServiceCounts


def _search_filter(search_query: str) -> QueryExpression:
    """Build an OR-combined case-insensitive "contains" filter over the searchable columns.

    ``search_query`` is expected to be already whitespace-stripped. An empty value yields a no-op
    filter, so the resulting query is identical to one without a search.
    """
    if not search_query:
        return NothingExpression()

    return Or(
        Hosts.name.contains(search_query, ignore_case=True),
        Hosts.alias.contains(search_query, ignore_case=True),
        Hosts.address.contains(search_query, ignore_case=True),
    )


class LiveStatusHostRepository:
    def __init__(self, *, connection: MultiSiteConnection) -> None:
        self._connection = connection

    def fetch(
        self,
        *,
        limit: int,
        search_query: str = "",
        sorters: Sequence[HostSort],
    ) -> Sequence[Host]:
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
            ],
            _search_filter(search_query),
            extra_headers=[
                # NOTE: Livestatus doesn't support sorting by multiple columns at the moment. The
                # resulting query will only take the first `OrderBy` statement and sort by that
                # criteria. We are leaving the wiring in for now and will investigate the ability to
                # sort by multiple columns in the livestatus client. Alternatively, we can apply
                # only the first filter in this query and then sort the other columns after limiting
                # the results (in Python).
                *[f"OrderBy: {s.column} {s.direction}" for s in sorters],
                f"Limit: {limit}",
            ],
        )

        with detailed_connection(self._connection) as conn:
            return [
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
                )
                for row in q.iterate(conn)
            ]

    def count(self, *, search_query: str = "") -> int:
        if not search_query:
            q = Query([Status.num_hosts])
            with detailed_connection(self._connection) as conn:
                return sum(row["num_hosts"] for row in q.iterate(conn))

        # A filtered total can't be read from the ``status`` table. Count the matches server-side
        # via ``Stats`` instead of transferring and counting every matching row. The ``Query`` class
        # can't emit ``Stats`` headers yet, so the query is assembled by hand from the shared filter.
        # The ``Stats`` count is the trailing column of each returned row; summing it across rows
        # adds up the per-site counts.
        filter_lines = (": ".join(line) for line in _search_filter(search_query).render())
        stats_query = "\n".join([f"GET {Hosts.__tablename__}", "Stats: state >= 0", *filter_lines])
        return sum(int(row[-1]) for row in self._connection.query(stats_query))
