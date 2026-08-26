#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""
Define concrete implementations for our repositories.

Our application should depend only interfaces as arguments, but receive a concrete implementation
when instantiated.
"""

from collections.abc import Mapping, Sequence, Set

from cmk.ccc.hostaddress import HostName
from cmk.ccc.site import SiteId
from cmk.gui.config import active_config
from cmk.livestatus_client import (
    LivestatusClient,
    MultiSiteConnection,
    ScheduleForcedServiceCheck,
)
from cmk.livestatus_client.expressions import And, NothingExpression, Or, QueryExpression
from cmk.livestatus_client.queries import detailed_connection, Query
from cmk.livestatus_client.tables import Hosts, Services
from cmk.livestatus_client.types import Column

from ._exceptions import ServiceNotFoundError
from ._models import (
    HostState,
    RescheduleTarget,
    Service,
    ServiceFilter,
    ServiceLabelValue,
    ServiceOptionalField,
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
        fields: Set[ServiceOptionalField],
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
                Services.acknowledged,
                Services.scheduled_downtime_depth,
                Services.notifications_enabled,
                Services.is_flapping,
                Services.staleness,
                Services.last_check,
                Services.last_state_change,
                Services.perf_data,
                Services.check_command,
                *(
                    column
                    for field, columns in _OPTIONAL_COLUMNS.items()
                    if field in fields
                    for column in columns
                ),
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
                        acknowledged=bool(row["acknowledged"]),
                        in_downtime=row["scheduled_downtime_depth"] > 0,
                        notifications_enabled=bool(row["notifications_enabled"]),
                        is_flapping=bool(row["is_flapping"]),
                        stale=row["staleness"] >= active_config.staleness_threshold,
                        summary=row["plugin_output"],
                        last_check=int(row["last_check"]) or None,
                        last_state_change=int(row["last_state_change"]),
                        perf_data=row["perf_data"],
                        check_command=row["check_command"],
                        labels=(
                            ServiceLabelValue.by_label(row["labels"], row["label_sources"])
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
                Services.is_flapping,
                Services.staleness,
                Services.host_alias,
                Services.host_state,
                Services.host_acknowledged,
                Services.host_scheduled_downtime_depth,
                Services.contact_groups,
                Services.long_plugin_output,
                Services.current_attempt,
                Services.max_check_attempts,
                Services.next_check,
                Services.tags,
                Services.labels,
                Services.label_sources,
                Services.perf_data,
                Services.check_command,
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
            last_check=int(row["last_check"]) or None,
            last_state_change=int(row["last_state_change"]),
            perf_data=row["perf_data"],
            check_command=row["check_command"],
            labels=ServiceLabelValue.by_label(row["labels"], row["label_sources"]),
            acknowledged=bool(row["acknowledged"]),
            in_downtime=row["scheduled_downtime_depth"] > 0,
            notifications_enabled=bool(row["notifications_enabled"]),
            is_flapping=bool(row["is_flapping"]),
            stale=row["staleness"] >= active_config.staleness_threshold,
            host_alias=row["host_alias"],
            host_state=HostState(row["host_state"]),
            host_acknowledged=bool(row["host_acknowledged"]),
            host_in_downtime=row["host_scheduled_downtime_depth"] > 0,
            contact_groups=list(row["contact_groups"]),
            long_output=row["long_plugin_output"],
            current_attempt=row["current_attempt"],
            max_check_attempts=row["max_check_attempts"],
            next_check=int(row["next_check"]) or None,
            tags=dict(row["tags"]),
            # The overview does not expose contacts, so its query does not read them.
            contacts=[],
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


# Everything beyond the columns every service row needs is read only when a caller asks
# for it, so a hidden column costs nothing.
_OPTIONAL_COLUMNS: Mapping[ServiceOptionalField, tuple[Column, ...]] = {
    ServiceOptionalField.LABELS: (Services.labels, Services.label_sources),
    ServiceOptionalField.TAGS: (Services.tags,),
    ServiceOptionalField.CONTACTS: (Services.contacts,),
    ServiceOptionalField.CONTACT_GROUPS: (Services.contact_groups,),
}


# The domain names the columns after what the table shows, which for some of them differs from the
# livestatus column they are read from.
_LIVESTATUS_COLUMN_OVERRIDES: Mapping[ServiceSortColumn, str] = {
    ServiceSortColumn.NAME: "description",
    ServiceSortColumn.SUMMARY: "plugin_output",
}


class LiveStatusServiceActions:
    def __init__(self, *, connection: MultiSiteConnection) -> None:
        self._connection = connection

    def reschedule(self, targets: Sequence[RescheduleTarget]) -> None:
        client = LivestatusClient(self._connection)
        for target in targets:
            client.command(
                ScheduleForcedServiceCheck(
                    host_name=HostName(target.host_name),
                    description=target.description,
                    check_time=target.check_time,
                ),
                SiteId(target.site_id),
            )


def _build_primary_sort(sorters: Sequence[ServiceSort]) -> str:
    """Pre-sort in livestatus so that a ``Limit`` cuts by the primary sorter rather than at random.

    This only approximates the final order: neither the secondary sorters nor the priority Checkmk's
    own services get in the default order can be expressed in an ``OrderBy``, so both are applied by
    the Python re-sort afterwards. In the default order, a host with more services than the limit
    whose names all sort before "Check_MK" would therefore lose those rows, same as in the legacy
    view.
    """
    if not sorters:
        # The default order sorts by name, so pre-sort the same way the Python re-sort will.
        return "OrderBy: description asc natural"

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

    return Or(
        Services.description.contains(query, ignore_case=True),
        Services.plugin_output.contains(query, ignore_case=True),
    )


def _build_host_services_filter(hostname: str, query: str) -> QueryExpression:
    return And(Services.host_name == hostname, _build_query_filter(query))
