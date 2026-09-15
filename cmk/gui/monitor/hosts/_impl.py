#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""
Define concrete implementations for our repositories.

Our application should depend only interfaces as arguments, but receive a concrete implementation
when instantiated.
"""

from collections.abc import Callable, Collection, Container, Mapping, Sequence, Set
from typing import cast

from cmk.ccc.hostaddress import HostName
from cmk.ccc.site import SiteId
from cmk.gui import sites
from cmk.gui.config import active_config
from cmk.gui.sites import SiteStates
from cmk.gui.utils.host_relation_kinds import kind_accepts
from cmk.gui.utils.host_relations import (
    parse_resolved_relations,
    RELATIONS_CUSTOM_VARIABLE,
    ResolvedRelation,
    reverse_direction,
)
from cmk.livestatus_client import (
    LivestatusClient,
    MultiSiteConnection,
    ScheduleForcedHostCheck,
)
from cmk.livestatus_client.expressions import And, NothingExpression, Or, QueryExpression
from cmk.livestatus_client.queries import detailed_connection, Query, ResultRow
from cmk.livestatus_client.tables import Hosts, Log
from cmk.livestatus_client.types import Column
from cmk.ruleset_matcher.labels import BuiltinLabelsKey

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
    MAX_RESOLVED_RELATIONS,
    RelatedHost,
    RelatedHostHealth,
    RescheduleTarget,
    ServiceCounts,
    UnixTimestamp,
)
from ._site import MonitorSites
from ._sorting import host_sorter


def _site_states() -> SiteStates:
    # Read through a function: the repository's own ``sites`` argument shadows the module.
    return sites.states()


def unavailable_sites(site_states: SiteStates) -> frozenset[str]:
    """The sites whose answer is missing rather than empty.

    A host on such a site is unknown, not absent, so relations to it are kept and shown as
    "cannot be read right now". "disabled" is the reader's own site selection instead of a site
    that could not be reached - and a host there was never queried, so the ``AuthUser`` filter
    never applied to it.
    """
    return frozenset(
        site_id
        for site_id, status in site_states.items()
        if status.get("state") not in ("online", "disabled")
    )


class LiveStatusHostRepository:
    def __init__(
        self,
        *,
        connection: MultiSiteConnection,
        folders: MonitorFolders | None = None,
        sites: MonitorSites | None = None,
        read_unavailable_sites: Callable[[], frozenset[str]] = lambda: unavailable_sites(
            _site_states()
        ),
    ) -> None:
        self._connection = connection
        # A folder is shown and searched by its Setup title, which Livestatus does not have. A
        # caller reading no folder needs none, hence the default that knows no titles.
        self._folders = folders if folders is not None else MonitorFolders()
        self._sites = sites if sites is not None else MonitorSites()
        self._read_unavailable_sites = read_unavailable_sites

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
        visible_relations: frozenset[tuple[str, str]] | None,
    ) -> Sequence[Host]:
        query_ = _sanitize_query(query)
        extra_headers = [
            *_split_filter_lines(filters),
            _build_primary_sort(sorters),
        ]
        if limit is not None:
            extra_headers.append(f"Limit: {limit}")
        wanted = _columns_to_read(fields, sorters)
        if HostOptionalField.NUM_RELATIONS in wanted and visible_relations is None:
            raise ValueError(
                "Counting relations needs the counterparts visible_relation_hosts() answers with."
            )
        q = Query(
            [
                Hosts.name,
                Hosts.state,
                Hosts.has_been_checked,
                Hosts.acknowledged,
                Hosts.scheduled_downtime_depth,
                Hosts.notifications_enabled,
                Hosts.comments,
                Hosts.modified_attributes_list,
                Hosts.active_checks_enabled,
                Hosts.accept_passive_checks,
                Hosts.in_notification_period,
                Hosts.in_service_period,
                Hosts.in_check_period,
                Hosts.is_flapping,
                Hosts.staleness,
                *(
                    column
                    for field, columns in _OPTIONAL_COLUMNS.items()
                    if field in wanted
                    for column in columns
                ),
            ],
            _build_query_filter(query_, fields, self._folders, self._sites),
            extra_headers=extra_headers,
        )
        # Only the relation count has to tell a site that did not answer from one that answered
        # nothing.
        unavailable = (
            frozenset[str]() if visible_relations is None else self._read_unavailable_sites()
        )

        with detailed_connection(self._connection) as conn:
            return sorted(
                [
                    Host(
                        name=row["name"],
                        alias=row.get("alias"),
                        address=row.get("address"),
                        state=_host_state(row),
                        site_id=row["site"],
                        service_counts=_optional_service_counts(row),
                        acknowledged=bool(row["acknowledged"]),
                        in_downtime=row["scheduled_downtime_depth"] > 0,
                        notifications_enabled=bool(row["notifications_enabled"]),
                        num_comments=len(row["comments"]),
                        active_checks_disabled=_manually_disabled(row, "active_checks_enabled"),
                        passive_checks_disabled=_manually_disabled(
                            row, "passive_checks_enabled", column="accept_passive_checks"
                        ),
                        in_notification_period=bool(row["in_notification_period"]),
                        in_service_period=bool(row["in_service_period"]),
                        in_check_period=bool(row["in_check_period"]),
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
                        num_relations=(
                            None
                            if visible_relations is None
                            else _count_relations(
                                row["custom_variables"].get(RELATIONS_CUSTOM_VARIABLE),
                                visible_relations,
                                unavailable,
                            )
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
                Hosts.has_been_checked,
                *_SERVICE_COUNT_COLUMNS,
                Hosts.acknowledged,
                Hosts.scheduled_downtime_depth,
                Hosts.notifications_enabled,
                Hosts.comments,
                Hosts.modified_attributes_list,
                Hosts.active_checks_enabled,
                Hosts.accept_passive_checks,
                Hosts.in_notification_period,
                Hosts.in_service_period,
                Hosts.in_check_period,
                Hosts.is_flapping,
                Hosts.staleness,
                Hosts.last_check,
                Hosts.last_state_change,
                Hosts.contact_groups,
                Hosts.tags,
                Hosts.labels,
                Hosts.label_sources,
                Hosts.filename,
                Hosts.custom_variables,
            ],
            Hosts.name == hostname,
        )
        try:
            row = q.fetchone(self._connection, True, only_site=SiteId(site_id))
        except ValueError:
            raise HostNotFoundError(f"Host {hostname!r} not found on site {site_id!r}") from None
        links = _known_relations(row["custom_variables"].get(RELATIONS_CUSTOM_VARIABLE))
        return Host(
            name=row["name"],
            alias=row["alias"],
            address=row["address"],
            state=_host_state(row),
            site_id=row["site"],
            service_counts=_service_counts(row),
            acknowledged=bool(row["acknowledged"]),
            in_downtime=row["scheduled_downtime_depth"] > 0,
            notifications_enabled=bool(row["notifications_enabled"]),
            num_comments=len(row["comments"]),
            active_checks_disabled=_manually_disabled(row, "active_checks_enabled"),
            passive_checks_disabled=_manually_disabled(
                row, "passive_checks_enabled", column="accept_passive_checks"
            ),
            in_notification_period=bool(row["in_notification_period"]),
            in_service_period=bool(row["in_service_period"]),
            in_check_period=bool(row["in_check_period"]),
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
            # Cut before the counterparts are read, so the query reading them is bounded too.
            relations=self._fetch_related_hosts(links[:MAX_RESOLVED_RELATIONS]),
            more_relations=len(links) > MAX_RESOLVED_RELATIONS,
        )

    def _fetch_related_hosts(self, links: Sequence[ResolvedRelation]) -> tuple[RelatedHost, ...]:
        """Read the state of the hosts a host is related to, in the order they were resolved.

        One query for all of them, asking only the sites the relations name - the export resolved
        every counterpart's site. Which of them reach the reader is :func:`_relation_is_shown`,
        the same rule the listing's relation count answers with.
        """
        if not links:
            return ()
        names = list(dict.fromkeys(link.host for link in links))
        q = Query(
            [
                Hosts.name,
                Hosts.state,
                Hosts.has_been_checked,
                *_SERVICE_COUNT_COLUMNS,
            ],
            And(
                Or(*(Hosts.name == name for name in names)),
                # The same criterion the relation count uses, so the two cannot come apart: a
                # host not carrying the variable is not anyone's counterpart as far as its own
                # core is concerned - what a site that has not activated the relation looks like.
                Hosts.custom_variable_names == RELATIONS_CUSTOM_VARIABLE,
            ),
        )
        # A name can exist on more than one site, so the site decides which host is meant.
        rows = {
            (row["site"], row["name"]): row
            for row in q.fetchall(
                self._connection, True, list(dict.fromkeys(SiteId(link.site) for link in links))
            )
        }
        unavailable = self._read_unavailable_sites()
        return tuple(
            RelatedHost(
                name=link.host,
                kind=link.kind,
                # The card names the other host, so it shows the end that host sits at in return.
                direction=reverse_direction(link.direction),
                site_id=link.site,
                health=(
                    None
                    if (row := rows.get((link.site, link.host))) is None
                    else _related_host_health(row)
                ),
            )
            for link in links
            if _relation_is_shown(link, known=rows, unavailable=unavailable)
        )

    def visible_relation_hosts(
        self, *, fields: Set[HostOptionalField], sorters: Sequence[HostSort]
    ) -> frozenset[tuple[str, str]] | None:
        """The hosts a relation may point at for this user, as ``(site, name)``.

        ``None`` when the listing shows no relation count and needs none of this.

        One query for the whole listing: every host that is anyone's counterpart carries the
        variable, and one missing from the answer is one the ``AuthUser`` filter dropped or one
        the core does not have - which is exactly what the host details leave out as well.

        Asked *before* the caller narrows the connection to the sites it lists: how many relations
        a host has is a property of the host, not of the reader's site filter.
        """
        if HostOptionalField.NUM_RELATIONS not in _columns_to_read(fields, sorters):
            return None
        q = Query([Hosts.name], Hosts.custom_variable_names == RELATIONS_CUSTOM_VARIABLE)
        with detailed_connection(self._connection) as conn:
            return frozenset((row["site"], row["name"]) for row in q.iterate(conn))

    def has_any_relations(self) -> bool:
        # Comparing a list column asks whether it contains the value. ``Limit: 1`` stops the core
        # at the first match, and the connection's ``AuthUser`` filter applies.
        q = Query(
            [Hosts.name],
            Hosts.custom_variable_names == RELATIONS_CUSTOM_VARIABLE,
            extra_headers=["Limit: 1"],
        )
        return q.first(self._connection) is not None

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
            for line in _build_query_filter(
                _sanitize_query(query), fields, self._folders, self._sites
            ).render()
        )
        return self._count_hosts(extra_lines=[*query_filter, *_split_filter_lines(filters)])

    def _count_hosts(self, *, extra_lines: Sequence[str] = ()) -> int:
        # A ``Stats`` count on the hosts table. Runs under the connection's ``AuthUser`` filter, so a
        # user without "see all" counts only the hosts they may see. The count is the trailing column
        # of each returned row; summing across rows adds up the per-site counts. A raw ``Stats`` query
        # returns untyped (string) columns, hence the explicit ``int`` conversion.
        stats_query = "\n".join((f"GET {Hosts.__tablename__}", "Stats: state >= 0", *extra_lines))
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


def _known_relations(raw: str | None) -> list[ResolvedRelation]:
    """The relations a core reported that this version can place, in the resolved order.

    Both reading sites go through here - the cards and the count - so a relation of a kind only a
    later version knows cannot make the number promise a card that is never rendered.
    """
    return [
        relation
        for relation in parse_resolved_relations(raw)
        if kind_accepts(relation.kind, relation.direction)
    ]


def _relation_is_shown(
    link: ResolvedRelation, *, known: Container[tuple[str, str]], unavailable: Container[str]
) -> bool:
    """Whether a relation reaches the reader at all.

    The one rule the relation count and the host details both answer with, so the number cannot
    promise cards that are not there: a counterpart a core answered for is shown, and so is one
    whose site could not be reached - the reader learns it exists. One the reader may not see, or
    that no site knows any more, is left out of both.
    """
    return (link.site, link.host) in known or link.site in unavailable


def _count_relations(
    raw: str | None, visible: frozenset[tuple[str, str]], unavailable: frozenset[str]
) -> int:
    """Count the relations of a host that reach the reader.

    The details stop rendering cards at ``MAX_RESOLVED_RELATIONS`` and say so; this number does
    not, so it stays the count of what the host is related to.
    """
    return sum(
        1
        for link in _known_relations(raw)
        if _relation_is_shown(link, known=visible, unavailable=unavailable)
    )


def _related_host_health(row: ResultRow) -> RelatedHostHealth:
    return RelatedHostHealth(
        state=_host_state(row),
        service_counts=_service_counts(row),
    )


def _sanitize_query(q: str) -> str:
    # TODO: decide on how we want to handle invalid regex? This will likely require coordinating
    # with frontend implementation to pass down errors to the response.
    return q.replace("*", ".*")


def _split_filter_lines(filters: HostFilter) -> list[str]:
    return filters.split("\n") if filters else []


_SEARCHED_FIELDS: Mapping[HostOptionalField, Callable[[str], QueryExpression]] = {
    HostOptionalField.ALIAS: lambda query: Hosts.alias.contains(query, ignore_case=True),
    HostOptionalField.ADDRESS: lambda query: Hosts.address.contains(query, ignore_case=True),
    HostOptionalField.LABELS: lambda query: Or(
        Hosts.label_names.contains(query, ignore_case=True),
        Hosts.label_values.contains(query, ignore_case=True),
    ),
    HostOptionalField.TAGS: lambda query: Or(
        Hosts.tag_names.contains(query, ignore_case=True),
        Hosts.tag_values.contains(query, ignore_case=True),
    ),
    HostOptionalField.CONTACTS: lambda query: Hosts.contacts.contains(query, ignore_case=True),
    HostOptionalField.CONTACT_GROUPS: lambda query: Hosts.contact_groups.contains(
        query, ignore_case=True
    ),
}


def _build_query_filter(
    query: str,
    fields: Set[HostOptionalField],
    folders: MonitorFolders,
    sites: MonitorSites,
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
    searched.extend(
        Hosts.labels.op("=", f"{BuiltinLabelsKey.SITE} {site_id}")
        for site_id in sites.matching(query)
    )

    return Or(Hosts.name.contains(query, ignore_case=True), *searched)


# The Livestatus column a sort column orders by, or ``None`` when no site's core has one - "site"
# is merged client-side, "num_relations" counted from the ``_RELATIONS`` variable, and "folder" is
# a file rather than the title Setup shows. For those the ``OrderBy`` header merely bounds which
# rows a ``Limit:`` keeps; the order the user sees is the one ``host_sorter()`` applies afterwards.
_LIVESTATUS_SORT_COLUMNS: Mapping[HostSortColumn, str | None] = {
    HostSortColumn.NAME: "name",
    HostSortColumn.ALIAS: "alias",
    HostSortColumn.ADDRESS: "address",
    HostSortColumn.STATE: "state",
    HostSortColumn.NUM_SERVICES: "num_services",
    HostSortColumn.NUM_SERVICES_OK: "num_services_ok",
    HostSortColumn.NUM_SERVICES_WARN: "num_services_warn",
    HostSortColumn.NUM_SERVICES_CRIT: "num_services_crit",
    HostSortColumn.NUM_SERVICES_UNKNOWN: "num_services_unknown",
    HostSortColumn.NUM_SERVICES_PENDING: "num_services_pending",
    HostSortColumn.LAST_CHECK: "last_check",
    HostSortColumn.LAST_STATE_CHANGE: "last_state_change",
    HostSortColumn.FOLDER: "filename",
    HostSortColumn.SITE_ID: None,
    HostSortColumn.NUM_RELATIONS: None,
}


# Everything beyond the columns every host row needs is read only when a caller asks for it,
# either through `fields` or by sorting on it.
_OPTIONAL_COLUMNS: Mapping[HostOptionalField, tuple[Column, ...]] = {
    HostOptionalField.ALIAS: (Hosts.alias,),
    HostOptionalField.ADDRESS: (Hosts.address,),
    HostOptionalField.NUM_SERVICES: (Hosts.num_services,),
    HostOptionalField.NUM_SERVICES_OK: (Hosts.num_services_ok,),
    HostOptionalField.NUM_SERVICES_WARN: (Hosts.num_services_warn,),
    HostOptionalField.NUM_SERVICES_CRIT: (Hosts.num_services_crit,),
    HostOptionalField.NUM_SERVICES_UNKNOWN: (Hosts.num_services_unknown,),
    HostOptionalField.NUM_SERVICES_PENDING: (Hosts.num_services_pending,),
    HostOptionalField.NUM_RELATIONS: (Hosts.custom_variables,),
    HostOptionalField.FOLDER: (Hosts.filename,),
    HostOptionalField.LAST_CHECK: (Hosts.last_check,),
    HostOptionalField.LAST_STATE_CHANGE: (Hosts.last_state_change,),
    HostOptionalField.LABELS: (Hosts.labels, Hosts.label_sources),
    HostOptionalField.TAGS: (Hosts.tags,),
    HostOptionalField.CONTACTS: (Hosts.contacts,),
    HostOptionalField.CONTACT_GROUPS: (Hosts.contact_groups,),
}

# The optional field a sort column needs read, or ``None`` when every query reads it anyway.
# Sorting happens in Python, so a sort column has to be read even when the response omits it.
_SORT_COLUMN_FIELDS: Mapping[HostSortColumn, HostOptionalField | None] = {
    HostSortColumn.NAME: None,
    HostSortColumn.STATE: None,
    HostSortColumn.SITE_ID: None,
    HostSortColumn.ALIAS: HostOptionalField.ALIAS,
    HostSortColumn.ADDRESS: HostOptionalField.ADDRESS,
    HostSortColumn.NUM_SERVICES: HostOptionalField.NUM_SERVICES,
    HostSortColumn.NUM_SERVICES_OK: HostOptionalField.NUM_SERVICES_OK,
    HostSortColumn.NUM_SERVICES_WARN: HostOptionalField.NUM_SERVICES_WARN,
    HostSortColumn.NUM_SERVICES_CRIT: HostOptionalField.NUM_SERVICES_CRIT,
    HostSortColumn.NUM_SERVICES_UNKNOWN: HostOptionalField.NUM_SERVICES_UNKNOWN,
    HostSortColumn.NUM_SERVICES_PENDING: HostOptionalField.NUM_SERVICES_PENDING,
    HostSortColumn.NUM_RELATIONS: HostOptionalField.NUM_RELATIONS,
    HostSortColumn.FOLDER: HostOptionalField.FOLDER,
    HostSortColumn.LAST_CHECK: HostOptionalField.LAST_CHECK,
    HostSortColumn.LAST_STATE_CHANGE: HostOptionalField.LAST_STATE_CHANGE,
}


def _columns_to_read(
    fields: Set[HostOptionalField], sorters: Sequence[HostSort]
) -> Set[HostOptionalField]:
    return set(fields) | {
        field for sorter in sorters if (field := _SORT_COLUMN_FIELDS[sorter.column]) is not None
    }


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


def _timestamp(value: float | None) -> UnixTimestamp | None:
    return None if value is None else int(value)


def _optional_service_counts(row: Mapping[str, object]) -> ServiceCounts | None:
    """The counts are read as a block, so one missing column means none were asked for."""
    return _service_counts(row) if "num_services" in row else None


#: Every column :func:`_service_counts` reads, for the queries that want them.
_SERVICE_COUNT_COLUMNS: tuple[Column, ...] = (
    Hosts.num_services,
    Hosts.num_services_ok,
    Hosts.num_services_warn,
    Hosts.num_services_crit,
    Hosts.num_services_unknown,
    Hosts.num_services_pending,
)


def _host_state(row: ResultRow) -> HostState:
    """A host that has never been checked has no state of its own yet."""
    return HostState.PENDING if row["has_been_checked"] == 0 else HostState(row["state"])


def _service_counts(row: Mapping[str, object]) -> ServiceCounts:
    return ServiceCounts(
        total=int(row["num_services"]),  # type: ignore[call-overload]
        ok=int(row["num_services_ok"]),  # type: ignore[call-overload]
        warn=int(row["num_services_warn"]),  # type: ignore[call-overload]
        crit=int(row["num_services_crit"]),  # type: ignore[call-overload]
        unknown=int(row["num_services_unknown"]),  # type: ignore[call-overload]
        pending=int(row["num_services_pending"]),  # type: ignore[call-overload]
    )


# Sorting by state hits the same limit-window imprecision as folder above: a host that has never
# been checked is ``HostState.PENDING`` - last in ``host_sorter()``'s ascending order - but its raw
# ``state`` column reports 0, indistinguishable there from a genuinely OK host. A listing longer
# than the limit, sorted by state, therefore shows the right rows in the right order only within
# the window the limit kept.
def _build_primary_sort(sorters: Sequence[HostSort]) -> str:
    if not sorters or (column := _LIVESTATUS_SORT_COLUMNS[sorters[0].column]) is None:
        return "OrderBy: name asc"

    primary = sorters[0]
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
