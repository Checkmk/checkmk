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
from cmk.livestatus_client.queries import detailed_connection, Query
from cmk.livestatus_client.tables import Hosts, Status

from ._models import Host, HostState, ServiceCounts


class LiveStatusHostRepository:
    def __init__(self, *, connection: MultiSiteConnection) -> None:
        self._connection = connection

    def fetch(self, *, limit: int) -> Sequence[Host]:
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
            extra_headers=[
                f"Limit: {limit}",
            ],
        )

        with detailed_connection(self._connection) as conn:
            return [
                Host(
                    name=row["name"],
                    alias=row["alias"],
                    ip=row["address"],
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

    def count(self) -> int:
        q = Query([Status.num_hosts])

        with detailed_connection(self._connection) as conn:
            return sum(row["num_hosts"] for row in q.iterate(conn))
