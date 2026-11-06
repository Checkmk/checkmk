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
from collections.abc import Callable, Collection, Mapping, Sequence, Set
from typing import cast

from cmk.ccc.hostaddress import HostName
from cmk.ccc.site import SiteId
from cmk.ccc.user import UserId
from cmk.gui.config import active_config
from cmk.gui.livestatus_utils.commands.acknowledgments import (
    acknowledge_service_problem,
    remove_acknowledgement,
)
from cmk.gui.livestatus_utils.commands.downtimes import recur_mode, RecurMode
from cmk.gui.monitor.command import ModifiableAttribute
from cmk.gui.monitor.hosts import reader_unavailable_sites
from cmk.gui.monitor.site_scope import MonitorSites
from cmk.livestatus_client import (
    ChangeServiceModifiedAttributes,
    Command,
    DeleteServiceDowntime,
    DisablePassiveServiceChecks,
    DisableServiceCheck,
    DisableServiceNotifications,
    EnablePassiveServiceChecks,
    EnableServiceCheck,
    EnableServiceNotifications,
    LivestatusClient,
    MultiSiteConnection,
    NotificationOption,
    ProcessServiceCheckResult,
    ScheduleForcedServiceCheck,
    ScheduleServiceDowntime,
    SendCustomServiceNotification,
)
from cmk.livestatus_client.expressions import And, NothingExpression, Or, QueryExpression
from cmk.livestatus_client.queries import detailed_connection, Query
from cmk.livestatus_client.tables import Downtimes, Hosts, Services
from cmk.livestatus_client.types import Column
from cmk.ruleset_matcher.labels import BuiltinLabelsKey

from ._exceptions import ServiceNotFoundError
from ._models import (
    CheckType,
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
    ServiceTarget,
)
from ._sorting import service_sorter


class LiveStatusHostServicesRepository:
    def __init__(
        self,
        *,
        connection: MultiSiteConnection,
        read_unavailable_sites: Callable[[], frozenset[str]] = reader_unavailable_sites,
    ) -> None:
        self._connection = connection
        self._read_unavailable_sites = read_unavailable_sites

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
        return _fetch_services(
            self._connection,
            _build_host_services_filter(hostname, _sanitize_query(query), fields),
            limit=limit,
            sorters=sorters,
            filters=filters,
            fields=fields,
        )

    def get_overview(self, *, hostname: str, service_name: str, site_id: str) -> ServiceOverview:
        q = Query(
            [
                Services.description,
                Services.host_name,
                Services.state,
                Services.has_been_checked,
                Services.plugin_output,
                Services.last_check,
                Services.last_state_change,
                Services.acknowledged,
                Services.scheduled_downtime_depth,
                Services.notifications_enabled,
                Services.comments,
                Services.modified_attributes_list,
                Services.active_checks_enabled,
                Services.accept_passive_checks,
                Services.in_notification_period,
                Services.in_service_period,
                Services.in_check_period,
                Services.in_passive_check_period,
                Services.is_flapping,
                Services.staleness,
                Services.host_alias,
                Services.host_state,
                Services.host_has_been_checked,
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
                Services.pnpgraph_present,
                Services.check_type,
                Services.cached_at,
                Services.cache_interval,
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
            state=(
                ServiceState.PENDING if row["has_been_checked"] == 0 else ServiceState(row["state"])
            ),
            summary=row["plugin_output"],
            last_check=int(row["last_check"]) or None,
            last_state_change=int(row["last_state_change"]) or None,
            perf_data=row["perf_data"],
            check_command=row["check_command"],
            has_graphs=row["pnpgraph_present"] == 1,
            active_checks_enabled=bool(row["active_checks_enabled"]),
            check_type=CheckType(row["check_type"]),
            cached_at=int(row["cached_at"]) or None,
            cache_interval=int(row["cache_interval"]),
            labels=ServiceLabelValue.by_label(row["labels"], row["label_sources"]),
            acknowledged=bool(row["acknowledged"]),
            in_downtime=row["scheduled_downtime_depth"] > 0,
            notifications_enabled=bool(row["notifications_enabled"]),
            num_comments=len(row["comments"]),
            active_checks_manually_disabled=_manually_disabled(row, "active_checks_enabled"),
            active_checks_manually_enabled=_manually_enabled(row, "active_checks_enabled"),
            passive_checks_disabled=_manually_disabled(
                row, "passive_checks_enabled", column="accept_passive_checks"
            ),
            in_notification_period=bool(row["in_notification_period"]),
            in_service_period=bool(row["in_service_period"]),
            in_check_period=_in_check_period(row),
            is_flapping=bool(row["is_flapping"]),
            stale=row["staleness"] >= active_config.staleness_threshold,
            host_alias=row["host_alias"],
            host_state=(
                HostState.PENDING
                if row["host_has_been_checked"] == 0
                else HostState(row["host_state"])
            ),
            host_acknowledged=bool(row["host_acknowledged"]),
            host_in_downtime=row["host_scheduled_downtime_depth"] > 0,
            contact_groups=list(row["contact_groups"]),
            groups=None,
            long_output=_unescape_livestatus_newlines(row["long_plugin_output"]),
            current_attempt=row["current_attempt"],
            max_check_attempts=row["max_check_attempts"],
            next_check=int(row["next_check"]) or None,
            tags=dict(row["tags"]),
            # The overview does not expose contacts, so its query does not read them.
            contacts=[],
        )

    def count_total(self, hostname: str) -> int:
        return self._count_services(hostname)

    def count_matched(
        self,
        hostname: str,
        *,
        query: str,
        filters: ServiceFilter,
        fields: Set[ServiceOptionalField],
    ) -> int:
        # A filtered total can't be read from the ``status`` table, so the matches are counted
        # server-side via ``Stats`` instead of transferring and counting every matching row.
        return self._count_services(hostname, query=query, filters=filters, fields=fields)

    def _count_services(
        self,
        hostname: str,
        *,
        query: str = "",
        filters: ServiceFilter = ServiceFilter(""),
        fields: Set[ServiceOptionalField] = frozenset(),
    ) -> int:
        return _count_services(
            self._connection,
            _build_host_services_filter(hostname, _sanitize_query(query), fields),
            filters,
        )

    def unreachable_sites(self) -> list[str]:
        return sorted(self._connection.dead_sites())

    def unavailable_sites(self) -> frozenset[str]:
        return self._read_unavailable_sites()


class LiveStatusServicesRepository:
    def __init__(self, *, connection: MultiSiteConnection, sites: MonitorSites) -> None:
        self._connection = connection
        self._sites = sites

    def fetch(
        self,
        *,
        limit: int | None,
        query: str,
        sorters: Sequence[ServiceSort],
        filters: ServiceFilter,
        fields: Set[ServiceOptionalField],
    ) -> Sequence[Service]:
        return _fetch_services(
            self._connection,
            self._search_filter(_sanitize_query(query), fields),
            limit=limit,
            sorters=sorters,
            filters=filters,
            fields=fields,
        )

    def count_total(self) -> int:
        return _count_services(self._connection, NothingExpression(), ServiceFilter(""))

    def count_matched(
        self, *, query: str, filters: ServiceFilter, fields: Set[ServiceOptionalField]
    ) -> int:
        return _count_services(
            self._connection, self._search_filter(_sanitize_query(query), fields), filters
        )

    def unreachable_sites(self) -> list[str]:
        return sorted(self._connection.dead_sites())

    def _search_filter(self, query: str, fields: Set[ServiceOptionalField]) -> QueryExpression:
        if not query:
            return NothingExpression()

        return Or(
            _build_query_filter(query, fields),
            Services.host_name.contains(query, ignore_case=True),
            *(
                Services.host_labels.op("=", f"{BuiltinLabelsKey.SITE} {site_id}")
                for site_id in self._sites.matching(query)
            ),
        )


def _fetch_services(
    connection: MultiSiteConnection,
    filter_expr: QueryExpression,
    *,
    limit: int | None,
    sorters: Sequence[ServiceSort],
    filters: ServiceFilter,
    fields: Set[ServiceOptionalField],
) -> list[Service]:
    extra_headers = [*_split_filter_lines(filters), _build_primary_sort(sorters)]

    if limit is not None:
        extra_headers.append(f"Limit: {limit}")

    q = Query(
        [
            Services.description,
            Services.host_name,
            Services.state,
            Services.has_been_checked,
            Services.plugin_output,
            Services.acknowledged,
            Services.scheduled_downtime_depth,
            Services.notifications_enabled,
            Services.comments,
            Services.modified_attributes_list,
            Services.active_checks_enabled,
            Services.accept_passive_checks,
            Services.in_notification_period,
            Services.in_service_period,
            Services.in_check_period,
            Services.in_passive_check_period,
            Services.is_flapping,
            Services.staleness,
            Services.last_check,
            Services.last_state_change,
            Services.perf_data,
            Services.check_command,
            Services.check_type,
            Services.cached_at,
            Services.cache_interval,
            Services.host_state,
            Services.host_has_been_checked,
            *(
                column
                for field, columns in _OPTIONAL_COLUMNS.items()
                if field in fields
                for column in columns
            ),
        ],
        filter_expr=filter_expr,
        extra_headers=extra_headers,
    )

    with detailed_connection(connection) as conn:
        return sorted(
            [
                Service(
                    name=row["description"],
                    host_name=row["host_name"],
                    site_id=row["site"],
                    state=(
                        ServiceState.PENDING
                        if row["has_been_checked"] == 0
                        else ServiceState(row["state"])
                    ),
                    host_state=(
                        HostState.PENDING
                        if row["host_has_been_checked"] == 0
                        else HostState(row["host_state"])
                    ),
                    acknowledged=bool(row["acknowledged"]),
                    in_downtime=row["scheduled_downtime_depth"] > 0,
                    notifications_enabled=bool(row["notifications_enabled"]),
                    num_comments=len(row["comments"]),
                    active_checks_manually_disabled=_manually_disabled(
                        row, "active_checks_enabled"
                    ),
                    active_checks_manually_enabled=_manually_enabled(row, "active_checks_enabled"),
                    passive_checks_disabled=_manually_disabled(
                        row, "passive_checks_enabled", column="accept_passive_checks"
                    ),
                    in_notification_period=bool(row["in_notification_period"]),
                    in_service_period=bool(row["in_service_period"]),
                    in_check_period=_in_check_period(row),
                    is_flapping=bool(row["is_flapping"]),
                    stale=row["staleness"] >= active_config.staleness_threshold,
                    summary=row["plugin_output"],
                    last_check=int(row["last_check"]) or None,
                    last_state_change=int(row["last_state_change"]) or None,
                    perf_data=row["perf_data"],
                    check_command=row["check_command"],
                    has_graphs=(
                        row["pnpgraph_present"] == 1 if "pnpgraph_present" in row else None
                    ),
                    active_checks_enabled=bool(row["active_checks_enabled"]),
                    check_type=CheckType(row["check_type"]),
                    cached_at=int(row["cached_at"]) or None,
                    cache_interval=int(row["cache_interval"]),
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
                    groups=list(row["groups"]) if "groups" in row else None,
                )
                for row in q.iterate(conn)
            ],
            key=service_sorter(sorters),
        )


def _count_services(
    connection: MultiSiteConnection, filter_expr: QueryExpression, filters: ServiceFilter
) -> int:
    stats_query = "\n".join(
        (
            f"GET {Services.__tablename__}",
            "Stats: state >= 0",
            *(": ".join(line) for line in filter_expr.render()),
            *_split_filter_lines(filters),
        )
    )
    return sum(int(row[-1]) for row in connection.query(stats_query))


# Everything beyond the columns every service row needs is read only when a caller asks
# for it, so a hidden column costs nothing.
_OPTIONAL_COLUMNS: Mapping[ServiceOptionalField, tuple[Column, ...]] = {
    ServiceOptionalField.LABELS: (Services.labels, Services.label_sources),
    ServiceOptionalField.TAGS: (Services.tags,),
    ServiceOptionalField.CONTACTS: (Services.contacts,),
    ServiceOptionalField.CONTACT_GROUPS: (Services.contact_groups,),
    ServiceOptionalField.GROUPS: (Services.groups,),
    ServiceOptionalField.GRAPHS_LINK: (Services.pnpgraph_present,),
}


# The livestatus column each sort column orders by. Every sort column is listed, also those whose
# livestatus column has the same name. `None` means there is no livestatus column to order by (the
# site), so those rows are ordered in Python only and `_build_primary_sort` skips the sorter.
_LIVESTATUS_SORT_COLUMNS: Mapping[ServiceSortColumn, str | None] = {
    ServiceSortColumn.NAME: "description",
    ServiceSortColumn.HOST_NAME: "host_name",
    ServiceSortColumn.SITE_ID: None,
    ServiceSortColumn.STATE: "state",
    ServiceSortColumn.SUMMARY: "plugin_output",
    ServiceSortColumn.LAST_CHECK: "last_check",
    ServiceSortColumn.LAST_STATE_CHANGE: "last_state_change",
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

    def send_custom_notification(
        self,
        targets: Sequence[ServiceTarget],
        *,
        author: UserId,
        comment: str,
        forced: bool,
        broadcast: bool,
    ) -> None:
        client = LivestatusClient(self._connection)
        option = NotificationOption(
            NotificationOption.FORCED.value * forced
            + NotificationOption.BROADCAST.value * broadcast
        )
        for target in targets:
            client.command(
                SendCustomServiceNotification(
                    HostName(target.host_name), option, author, comment, target.description
                ),
                SiteId(target.site_id),
            )

    def fake_check_result(
        self, targets: Sequence[ServiceTarget], *, state: int, output: str
    ) -> None:
        client = LivestatusClient(self._connection)
        for target in targets:
            client.command(
                ProcessServiceCheckResult(
                    HostName(target.host_name), state, output, target.description
                ),
                SiteId(target.site_id),
            )

    def toggle_attribute(
        self, targets: Sequence[ServiceTarget], attribute: ModifiableAttribute, *, enabled: bool
    ) -> None:
        command = _SERVICE_ATTRIBUTE_COMMANDS[attribute][enabled]
        client = LivestatusClient(self._connection)
        for target in targets:
            client.command(
                command(HostName(target.host_name), target.description), SiteId(target.site_id)
            )

    def reset_modified_attributes(self, targets: Sequence[ServiceTarget]) -> None:
        client = LivestatusClient(self._connection)
        for target in targets:
            client.command(
                ChangeServiceModifiedAttributes(HostName(target.host_name), 0, target.description),
                SiteId(target.site_id),
            )

    def acknowledge(
        self,
        targets: Sequence[ServiceTarget],
        *,
        author: UserId,
        comment: str,
        sticky: bool,
        persistent: bool,
        notify: bool,
        expire_on: dt.datetime | None,
    ) -> int:
        problems = [target for target, state in self._found(targets).items() if state]
        for target in problems:
            acknowledge_service_problem(
                self._connection,
                SiteId(target.site_id),
                HostName(target.host_name),
                target.description,
                sticky=sticky,
                notify=notify,
                persistent=persistent,
                user=author,
                comment=comment,
                expire_on=expire_on,
            )
        return len(problems)

    def remove_acknowledgements(self, targets: Sequence[ServiceTarget]) -> int:
        visible = self._visible(targets)
        for target in visible:
            remove_acknowledgement(
                self._connection,
                SiteId(target.site_id),
                HostName(target.host_name),
                target.description,
            )
        return len(visible)

    def schedule_downtime(
        self,
        targets: Sequence[ServiceTarget],
        *,
        author: UserId,
        comment: str,
        start_time: dt.datetime,
        end_time: dt.datetime,
        recur: RecurMode,
        duration_minutes: int,
    ) -> int:
        visible = self._found(targets)
        client = LivestatusClient(self._connection)
        mode = recur_mode(recur, duration_minutes)
        for target in visible:
            client.command(
                ScheduleServiceDowntime(
                    host_name=HostName(target.host_name),
                    description=target.description,
                    start_time=start_time,
                    end_time=end_time,
                    recur_mode=mode,
                    trigger_id=0,
                    duration=60 * duration_minutes,
                    user=author,
                    comment=comment,
                ),
                SiteId(target.site_id),
            )
        return len(visible)

    def remove_downtimes(self, targets: Sequence[ServiceTarget]) -> int:
        wanted = set(targets)
        rows = Query(
            [Downtimes.id, Downtimes.host_name, Downtimes.service_description],
            _match(targets, Downtimes.host_name, Downtimes.service_description),
        ).fetchall(self._connection, include_site_ids=True, only_sites=_sites_of(targets))
        client = LivestatusClient(self._connection)
        removed: set[ServiceTarget] = set()
        for row in rows:
            target = ServiceTarget(
                site_id=row.site, host_name=row.host_name, description=row.service_description
            )
            # A site may also monitor a service of a name selected only on another site.
            if target in wanted:
                client.command(DeleteServiceDowntime(row.id), SiteId(row.site))
                removed.add(target)
        return len(removed)

    def _found(self, targets: Sequence[ServiceTarget]) -> dict[ServiceTarget, int]:
        if not (visible := self._visible(targets)):
            raise ServiceNotFoundError("None of the services was found.")
        return visible

    def _visible(self, targets: Sequence[ServiceTarget]) -> dict[ServiceTarget, int]:
        """The targets the user may see, the only ones a command may reach, with their states."""
        if not targets:
            return {}
        wanted = set(targets)
        rows = Query(
            [Services.host_name, Services.description, Services.state],
            _match(targets, Services.host_name, Services.description),
        ).fetchall(self._connection, include_site_ids=True, only_sites=_sites_of(targets))
        return {
            target: row.state
            for row in rows
            if (
                target := ServiceTarget(
                    site_id=row.site, host_name=row.host_name, description=row.description
                )
            )
            in wanted
        }


def _match(
    targets: Sequence[ServiceTarget], host_column: Column, description_column: Column
) -> QueryExpression:
    return Or(
        *(
            And(host_column == host_name, description_column == description)
            for host_name, description in dict.fromkeys(
                (target.host_name, target.description) for target in targets
            )
        )
    )


def _sites_of(targets: Sequence[ServiceTarget]) -> list[SiteId]:
    return sorted({SiteId(target.site_id) for target in targets})


# The command disabling an attribute, then the one enabling it, indexed by `enabled`.
_SERVICE_ATTRIBUTE_COMMANDS: Mapping[
    ModifiableAttribute, tuple[Callable[[HostName, str], Command], ...]
] = {
    ModifiableAttribute.NOTIFICATIONS: (DisableServiceNotifications, EnableServiceNotifications),
    ModifiableAttribute.ACTIVE_CHECKS: (DisableServiceCheck, EnableServiceCheck),
    ModifiableAttribute.PASSIVE_CHECKS: (DisablePassiveServiceChecks, EnablePassiveServiceChecks),
}


def _build_primary_sort(sorters: Sequence[ServiceSort]) -> str:
    """Pre-sort in livestatus so that a ``Limit`` cuts by the primary sorter rather than at random.

    This only approximates the final order: neither the secondary sorters nor the priority Checkmk's
    own services get in the default order can be expressed in an ``OrderBy``, so both are applied by
    the Python re-sort afterwards. In the default order, a host with more services than the limit
    whose names all sort before "Check_MK" would therefore lose those rows, same as in the legacy
    view. The same holds for every multi-column order, e.g. the All services default of site, host
    name, then service name: when the limit cuts through a host, that host keeps whichever of its
    services the core returned first, not its first ones by name.

    A sorter without a livestatus column, like the site, is skipped: the first sorter that has one
    is what orders the rows within each site's answer.
    """
    sortable = (
        (sorter, column)
        for sorter in sorters
        if (column := _LIVESTATUS_SORT_COLUMNS[sorter.column]) is not None
    )
    if (first := next(sortable, None)) is None:
        # The default order sorts by name, so pre-sort the same way the Python re-sort will.
        return "OrderBy: description asc natural"

    primary, column = first
    natural_sort_flag = " natural" if primary.column.natural_sort else ""

    return f"OrderBy: {column} {primary.direction}{natural_sort_flag}"


def _in_check_period(row: Mapping[str, object]) -> bool:
    """Whether a service is currently being checked at all.

    A service has two periods, one per check kind, and leaving either of them stops the checks
    it governs - so it counts as checked only while inside both.
    """
    return bool(row["in_check_period"]) and bool(row["in_passive_check_period"])


def _unescape_livestatus_newlines(text: str) -> str:
    return text.replace("\\n", "\n")


def _manually_disabled(
    row: Mapping[str, object], attribute: str, *, column: str | None = None
) -> bool:
    """Whether a check setting was turned off by a user rather than left off by configuration.

    Livestatus reports the setting alone, which is also 0 for everything a plugin never
    enables; only a mention in ``modified_attributes_list`` says a user switched it off. Pass
    ``column`` where the setting's own column is named differently from the modified attribute.
    """
    modified = cast(Collection[str], row["modified_attributes_list"])
    return attribute in modified and not row[column or attribute]


def _manually_enabled(row: Mapping[str, object], attribute: str) -> bool:
    """Whether a check setting was turned on by a user, as the legacy views mark it."""
    return attribute in cast(Collection[str], row["modified_attributes_list"]) and bool(
        row[attribute]
    )


def _sanitize_query(q: str) -> str:
    # TODO: decide on how we want to handle invalid regex? This will likely require coordinating
    # with frontend implementation to pass down errors to the response.
    return q.replace("*", ".*")


def _split_filter_lines(filters: ServiceFilter) -> list[str]:
    return filters.split("\n") if filters else []


_SEARCHED_FIELDS: Mapping[ServiceOptionalField, Callable[[str], QueryExpression]] = {
    ServiceOptionalField.LABELS: lambda query: Or(
        Services.label_names.contains(query, ignore_case=True),
        Services.label_values.contains(query, ignore_case=True),
    ),
    ServiceOptionalField.TAGS: lambda query: Or(
        Services.tag_names.contains(query, ignore_case=True),
        Services.tag_values.contains(query, ignore_case=True),
    ),
    ServiceOptionalField.CONTACTS: lambda query: Services.contacts.contains(
        query, ignore_case=True
    ),
    ServiceOptionalField.CONTACT_GROUPS: lambda query: Services.contact_groups.contains(
        query, ignore_case=True
    ),
    ServiceOptionalField.GROUPS: lambda query: Services.groups.contains(query, ignore_case=True),
}


def _build_query_filter(query: str, fields: Set[ServiceOptionalField]) -> QueryExpression:
    if not query:
        return NothingExpression()

    return Or(
        Services.description.contains(query, ignore_case=True),
        Services.plugin_output.contains(query, ignore_case=True),
        *(build(query) for field, build in _SEARCHED_FIELDS.items() if field in fields),
    )


def _build_host_services_filter(
    hostname: str, query: str, fields: Set[ServiceOptionalField]
) -> QueryExpression:
    return And(Services.host_name == hostname, _build_query_filter(query, fields))
