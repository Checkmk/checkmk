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

from cmk.ccc.site import SiteId
from cmk.livestatus_client import MultiSiteConnection
from cmk.livestatus_client.expressions import And, NothingExpression, QueryExpression
from cmk.livestatus_client.queries import detailed_connection, Query
from cmk.livestatus_client.tables import Hosts, Services

from ._exceptions import ServiceNotFoundError
from ._models import (
    Service,
    ServiceFilter,
    ServiceOverview,
    ServiceSort,
    ServiceSortColumn,
    ServiceState,
)
from ._sorting import service_sorter


class LiveStatusHostServicesRepository:
    def __init__(self, *, connection: MultiSiteConnection) -> None:
        self._connection = connection

    def host_exists(self, hostname: str) -> bool:
        q = Query([Hosts.name], Hosts.name == hostname, extra_headers=["Limit: 1"])
        return q.first(self._connection) is not None

    def fetch(
        self,
        hostname: str,
        *,
        limit: int | None,
        query: str,
        sorters: Sequence[ServiceSort],
        filters: ServiceFilter,
    ) -> Sequence[Service]:
        extra_headers = [*filters.splitlines(), _build_primary_sort(sorters)]

        if limit is not None:
            extra_headers.append(f"Limit: {limit}")

        q = Query(
            [
                Services.description,
                Services.host_name,
                Services.state,
                Services.plugin_output,
                Services.last_check,
                Services.last_state_change,
            ],
            filter_expr=_build_host_services_filter(hostname, _sanitize_query(query)),
            extra_headers=extra_headers,
        )

        with detailed_connection(self._connection) as conn:
            return sorted(
                [
                    Service(
                        name=row["description"],
                        state=ServiceState(row["state"]),
                        summary=row["plugin_output"],
                        last_check=dt.datetime.fromtimestamp(row["last_check"], tz=dt.UTC),
                        last_state_change=dt.datetime.fromtimestamp(
                            row["last_state_change"], tz=dt.UTC
                        ),
                    )
                    for row in q.iterate(conn)
                ],
                key=service_sorter(sorters),
            )

    def get_overview(self, *, hostname: str, service_name: str, site_id: str) -> ServiceOverview:
        q = Query(
            [
                Services.description,
                Services.host_name,
                Services.state,
                Services.plugin_output,
                Services.last_check,
                Services.last_state_change,
                Services.acknowledged,
                Services.scheduled_downtime_depth,
                Services.notifications_enabled,
            ],
            And(Services.host_name == hostname, Services.description == service_name),
        )
        try:
            row = q.fetchone(self._connection, True, only_site=SiteId(site_id))
        except ValueError:
            raise ServiceNotFoundError(
                f"Service {service_name!r} of host {hostname!r} not found on site {site_id!r}"
            ) from None

        return ServiceOverview(
            name=row["description"],
            host_name=row["host_name"],
            site_id=row["site"],
            state=ServiceState(row["state"]),
            summary=row["plugin_output"],
            last_check=dt.datetime.fromtimestamp(row["last_check"], tz=dt.UTC),
            last_state_change=dt.datetime.fromtimestamp(row["last_state_change"], tz=dt.UTC),
            acknowledged=bool(row["acknowledged"]),
            in_downtime=row["scheduled_downtime_depth"] > 0,
            notifications_enabled=bool(row["notifications_enabled"]),
        )

    def count_total(self, hostname: str) -> int:
        return self._count_services(hostname)

    def count_matched(self, hostname: str, *, query: str, filters: ServiceFilter) -> int:
        # A filtered total can't be read from the ``status`` table, so the matches are counted
        # server-side via ``Stats`` instead of transferring and counting every matching row.
        return self._count_services(hostname, query=query, filters=filters)

    def _count_services(
        self, hostname: str, *, query: str = "", filters: ServiceFilter = ServiceFilter("")
    ) -> int:
        filter_expr = _build_host_services_filter(hostname, _sanitize_query(query))
        stats_query = "\n".join(
            [
                f"GET {Services.__tablename__}",
                "Stats: state >= 0",
                *(": ".join(line) for line in filter_expr.render()),
                *filters.splitlines(),
            ]
        )
        return sum(int(row[-1]) for row in self._connection.query(stats_query))


# The domain names the columns after what the table shows, which for some of them differs from the
# livestatus column they are read from.
_LIVESTATUS_COLUMN_OVERRIDES: Mapping[ServiceSortColumn, str] = {
    ServiceSortColumn.NAME: "description",
    ServiceSortColumn.SUMMARY: "plugin_output",
}


def _build_primary_sort(sorters: Sequence[ServiceSort]) -> str:
    if not sorters:
        return "OrderBy: description asc"

    primary = sorters[0]
    column = _LIVESTATUS_COLUMN_OVERRIDES.get(primary.column, primary.column.value)
    natural_sort_flag = " natural" if primary.column.natural_sort else ""

    return f"OrderBy: {column} {primary.direction}{natural_sort_flag}"


def _sanitize_query(q: str) -> str:
    # TODO: decide on how we want to handle invalid regex? This will likely require coordinating
    # with frontend implementation to pass down errors to the response.
    return q.replace("*", ".*")


def _build_query_filter(query: str) -> QueryExpression:
    if not query:
        return NothingExpression()

    return Services.description.contains(query, ignore_case=True)


def _build_host_services_filter(hostname: str, query: str) -> QueryExpression:
    return And(Services.host_name == hostname, _build_query_filter(query))
