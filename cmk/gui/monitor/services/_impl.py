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

from cmk.livestatus_client import MultiSiteConnection
from cmk.livestatus_client.queries import detailed_connection, Query
from cmk.livestatus_client.tables import Hosts, Services

from ._models import Service, ServiceSort, ServiceSortColumn, ServiceState
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
        sorters: Sequence[ServiceSort],
    ) -> Sequence[Service]:
        extra_headers = [_build_primary_sort(sorters)]

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
            filter_expr=Services.host_name == hostname,
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

    def count_total(self, hostname: str) -> int:
        filter_expr = Services.host_name == hostname
        query = "\n".join(
            [
                f"GET {Services.__tablename__}",
                "Stats: state >= 0",
                *(": ".join(line) for line in filter_expr.render()),
            ]
        )
        return sum(int(row[-1]) for row in self._connection.query(query))


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
