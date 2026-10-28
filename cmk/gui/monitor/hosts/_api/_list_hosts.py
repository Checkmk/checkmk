#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Callable, Collection, Sequence, Set
from http import HTTPStatus
from typing import Annotated, Final, Self

from annotated_types import Interval
from pydantic import PlainValidator

from cmk.ccc.site import SiteId
from cmk.gui import sites
from cmk.gui.monitor.setup_folders import SetupFolderSource
from cmk.gui.monitor.shared import FILTER_NODE, FilterNode, HostStateLabel
from cmk.gui.monitor.site_scope import MonitorSite, MonitorSites
from cmk.gui.monitor.table_widget import TableRows
from cmk.gui.openapi.framework import (
    ApiContext,
    APIVersion,
    EndpointBehavior,
    EndpointDoc,
    EndpointHandler,
    EndpointMetadata,
    EndpointPermissions,
    VersionedEndpoint,
)
from cmk.gui.openapi.framework.model import api_field, api_model, ApiOmitted
from cmk.gui.openapi.utils import RestAPIRequestGeneralException
from cmk.gui.type_defs import VisualContext
from cmk.livestatus_client import SiteConfigurations
from cmk.web.utils import permission_verification as permissions

from .._customer import customer_resolver
from .._exceptions import InvalidFilterError
from .._folder import MonitorFolders
from .._impl import LiveStatusHostRepository
from .._models import (
    Host,
    HostFilter,
    HostLabelValue,
    HostOptionalField,
    HostSort,
    HostSortColumn,
    HostSortDirection,
    UnixTimestamp,
)
from .._repositories import HostRepository
from .._table_catalog import DEFAULT_HOST_SORT, HOST_TABLE
from ..context_filters import translate_filters
from ._family import MONITOR_HOSTS_FAMILY
from ._filters import parse_as_livestatus_filter, scope_filter_by_site, SiteScopedFilter
from ._modes import build_host_modes, ModeInfo
from ._urls import host_view_link
from ._validators import parse_host_search_query, parse_host_sort_options

# View-local limits, deliberately not coupled to the global soft/hard query limit settings so they
# never affect the legacy views.
_MIN_NUMBER_OF_HOSTS = 0
_MAX_NUMBER_OF_HOSTS = 5_000
_DEFAULT_LIMIT = 1_000

# The row limits the All hosts page offers: the default first, the maximum last.
LIMIT_TIERS: Final = (_DEFAULT_LIMIT, _MAX_NUMBER_OF_HOSTS)

_DEFAULT_FIELDS: frozenset[HostOptionalField] = frozenset(
    {
        HostOptionalField.ADDRESS,
        HostOptionalField.NUM_SERVICES,
        HostOptionalField.NUM_SERVICES_OK,
        HostOptionalField.NUM_SERVICES_WARN,
        HostOptionalField.NUM_SERVICES_CRIT,
        HostOptionalField.NUM_SERVICES_UNKNOWN,
        HostOptionalField.NUM_SERVICES_PENDING,
    }
)


@api_model
class HostEntry:
    name: str = api_field(description="Host name", example="web-server-01")
    state: HostStateLabel = api_field(
        description=(
            "Host state. 'PENDING' means the host has never been checked, i.e. its state is "
            "still pending the first check result"
        ),
        example="UP",
    )
    is_flapping: bool = api_field(description="Whether the host state is flapping", example=False)
    stale: bool = api_field(
        description="Whether the host hasn't been checked recently enough", example=False
    )
    site_id: str = api_field(description="Site ID", example="local")
    address: str | ApiOmitted = api_field(
        description="Primary IP address",
        example="10.0.0.1",
        default_factory=ApiOmitted,
    )
    alias: str | ApiOmitted = api_field(
        description="Host alias",
        example="Web Server",
        default_factory=ApiOmitted,
    )
    num_services: int | ApiOmitted = api_field(
        description="Total number of services",
        example=48,
        default_factory=ApiOmitted,
    )
    num_services_ok: int | ApiOmitted = api_field(
        description="Number of services in OK state",
        example=42,
        default_factory=ApiOmitted,
    )
    num_services_warn: int | ApiOmitted = api_field(
        description="Number of services in WARNING state",
        example=3,
        default_factory=ApiOmitted,
    )
    num_services_crit: int | ApiOmitted = api_field(
        description="Number of services in CRITICAL state",
        example=1,
        default_factory=ApiOmitted,
    )
    num_services_unknown: int | ApiOmitted = api_field(
        description="Number of services in UNKNOWN state",
        example=0,
        default_factory=ApiOmitted,
    )
    num_services_pending: int | ApiOmitted = api_field(
        description="Number of services in PENDING state",
        example=2,
        default_factory=ApiOmitted,
    )
    folder: str | ApiOmitted = api_field(
        description=(
            "The title Setup gives the folder the host is configured in: the titles down to it, "
            "'Main' for the root folder. Empty when Setup knows no such folder, e.g. the host "
            "isn't managed via Setup or a remote site owns it."
        ),
        example="Data center Munich / Rack 1",
        default_factory=ApiOmitted,
    )
    last_check: UnixTimestamp | None | ApiOmitted = api_field(
        description=(
            "Unix timestamp of the host's last check. Null for hosts that have never been "
            "checked, i.e. those still pending their first check."
        ),
        example=1752405510,
        default_factory=ApiOmitted,
    )
    last_state_change: UnixTimestamp | None | ApiOmitted = api_field(
        description=(
            "Unix timestamp of the host's last state change. Null for hosts that have never "
            "been checked, i.e. those still pending their first check."
        ),
        example=1752405540,
        default_factory=ApiOmitted,
    )
    labels: dict[str, HostLabelValue] | ApiOmitted = api_field(
        description="Host labels, keyed by label name. Omitted when the host has none.",
        example={"cmk/site": HostLabelValue(value="heute", source="discovered")},
        default_factory=ApiOmitted,
    )
    tags: dict[str, str] | ApiOmitted = api_field(
        description="Host tags, keyed by tag group. Omitted when the host has none.",
        example={"criticality": "prod"},
        default_factory=ApiOmitted,
    )
    contacts: list[str] | ApiOmitted = api_field(
        description="Contacts responsible for this host. Omitted when it has none.",
        example=["hh"],
        default_factory=ApiOmitted,
    )
    contact_groups: list[str] | ApiOmitted = api_field(
        description="Contact groups this host is in. Omitted when it is in none.",
        example=["all"],
        default_factory=ApiOmitted,
    )
    groups: list[str] | ApiOmitted = api_field(
        description="Host groups this host is in. Omitted when it is in none.",
        example=["linux"],
        default_factory=ApiOmitted,
    )
    customer: str | ApiOmitted = api_field(
        description=(
            "Name of the customer the host belongs to, which is the customer of the site "
            "monitoring it. Only editions with multi-tenancy support assign customers, so this "
            "is omitted everywhere else."
        ),
        example="Customer A",
        default_factory=ApiOmitted,
    )
    modes: list[ModeInfo] | ApiOmitted = api_field(
        description=(
            "Active host modes (e.g. scheduled downtime, acknowledgement) rendered as linked "
            "icons. Empty when the host is in none of these modes."
        ),
        example=[],
        default_factory=ApiOmitted,
    )
    legacy_host_status_link: str = api_field(
        description="URL to legacy host status view",
        example="view.py?view_name=hoststatus&host=web-server-01&site=local",
    )
    num_relations: int | ApiOmitted = api_field(
        description=(
            "Number of hosts related to this host via the Setup 'Relations' feature (management "
            "board / OS hosts). The related hosts themselves are shown in the host details, so "
            "the listing carries the count only. 0 when the host has no relations."
        ),
        example=2,
        default_factory=ApiOmitted,
    )

    setup_access: bool | ApiOmitted = api_field(
        description=(
            "Whether the user may open the host in Setup, where it may be restricted to the "
            "contact groups its permissions name. False for a host Setup does not know, such as "
            "one added straight to the monitoring core."
        ),
        example=True,
        default_factory=ApiOmitted,
    )

    @classmethod
    def from_domain(cls, host: Host, fields: Set[HostOptionalField], customer: str | None) -> Self:
        def included[T](field: HostOptionalField, value: T | None) -> T | ApiOmitted:
            """Return the value only if it was asked for and therefore actually read."""
            return value if field in fields and value is not None else ApiOmitted()

        def included_timestamp(
            field: HostOptionalField, value: UnixTimestamp | None
        ) -> UnixTimestamp | None | ApiOmitted:
            """Like :func:`included`, but null for a host that was never checked.

            Livestatus reports 0 for both timestamps of such a host.
            """
            if field not in fields or value is None:
                return ApiOmitted()
            return value or None

        return cls(
            name=host.name,
            state=host.state_label,
            is_flapping=host.is_flapping,
            stale=host.stale,
            site_id=host.site_id,
            address=included(HostOptionalField.ADDRESS, host.address),
            alias=included(HostOptionalField.ALIAS, host.alias),
            num_services=included(HostOptionalField.NUM_SERVICES, host.num_services),
            num_services_ok=included(HostOptionalField.NUM_SERVICES_OK, host.num_services_ok),
            num_services_warn=included(HostOptionalField.NUM_SERVICES_WARN, host.num_services_warn),
            num_services_crit=included(HostOptionalField.NUM_SERVICES_CRIT, host.num_services_crit),
            num_services_unknown=included(
                HostOptionalField.NUM_SERVICES_UNKNOWN, host.num_services_unknown
            ),
            num_services_pending=included(
                HostOptionalField.NUM_SERVICES_PENDING, host.num_services_pending
            ),
            folder=included(HostOptionalField.FOLDER, host.folder),
            last_check=included_timestamp(HostOptionalField.LAST_CHECK, host.last_check),
            last_state_change=included_timestamp(
                HostOptionalField.LAST_STATE_CHANGE, host.last_state_change
            ),
            labels=included(HostOptionalField.LABELS, host.labels),
            tags=included(HostOptionalField.TAGS, host.tags),
            contacts=included(HostOptionalField.CONTACTS, host.contacts),
            contact_groups=included(HostOptionalField.CONTACT_GROUPS, host.contact_groups),
            groups=included(HostOptionalField.GROUPS, host.groups),
            customer=ApiOmitted() if customer is None else customer,
            modes=build_host_modes(host) or ApiOmitted(),
            legacy_host_status_link=host_view_link("hoststatus", host),
            num_relations=included(HostOptionalField.NUM_RELATIONS, host.num_relations),
            setup_access=included(HostOptionalField.SETUP_ACCESS, host.setup_access),
        )


@api_model
class HostsPageMeta:
    limit: int | None = api_field(description="Applied row limit.", example=1000)
    matched: int = api_field(description="Total matched hosts", example=42)
    total: int = api_field(description="Total number of hosts", example=1234)
    fields: Set[HostOptionalField] = api_field(
        description="Applied optional fields.",
        example=["address", "num_services"],
    )
    unreachable_sites: list[str] = api_field(
        description=(
            "IDs of the sites that could not be reached. Their hosts are missing from the hosts, "
            "'matched' and 'total'."
        ),
        example=["remote_1"],
    )


@api_model
class HostsResponse:
    hosts: list[HostEntry] = api_field(description="The hosts for this query", example=[])
    meta: HostsPageMeta = api_field(description="Page metadata")


@api_model
class HostsRequestBody:
    limit: Annotated[int, Interval(ge=_MIN_NUMBER_OF_HOSTS, le=_MAX_NUMBER_OF_HOSTS)] | None = (
        api_field(
            description=(
                "Number of hosts to return. Pass null to remove the limit entirely; this requires "
                "the 'general.ignore_hard_limit' permission and otherwise falls back to the maximum "
                f"of {_MAX_NUMBER_OF_HOSTS}."
            ),
            example=_DEFAULT_LIMIT,
            default=_DEFAULT_LIMIT,
        )
    )
    sort: Annotated[
        list[HostSort] | ApiOmitted,
        PlainValidator(func=parse_host_sort_options, json_schema_input_type=list[str]),
    ] = api_field(
        description=(
            "Sort options. Each value is 'column:direction', e.g. 'name:asc'. "
            f"Allowed columns: {HostSortColumn.options()}. "
            f"Allowed directions: {HostSortDirection.options()}. "
            "Multiple values define a multi-column sort applied in the given order; a column must "
            "not be repeated."
        ),
        example="name:asc",
        default_factory=ApiOmitted,
    )
    q: Annotated[
        str | ApiOmitted,
        PlainValidator(func=parse_host_search_query, json_schema_input_type=str),
    ] = api_field(
        description=(
            "Search text, matched against the host name, the site, the customer and every "
            "text field asked for through `fields` (alias, address, folder, labels, tags, "
            "contacts, contact groups, host groups). Site and customer are searched whether or "
            "not their column is shown. Omit or pass empty string to return all hosts."
        ),
        example="web-server",
        default_factory=ApiOmitted,
    )
    filter: FilterNode | ApiOmitted = api_field(
        description="Boolean filter expression tree. Omit to return all hosts.",
        default_factory=ApiOmitted,
    )
    fields: frozenset[HostOptionalField] | ApiOmitted = api_field(
        description=(
            f"Optional field names to include. Allowed values: {HostOptionalField.options()}. "
            "Omit to return default fields."
        ),
        example=["address", "num_services"],
        default_factory=ApiOmitted,
    )


def _list_hosts(
    api_context: ApiContext, body: HostsRequestBody, folders: MonitorFolders
) -> HostsResponse:
    # A `None` request means "remove the limit". We only honor that for users allowed to ignore
    # the hard limit; everyone else is clamped to the safety ceiling. Numeric requests are already
    # bounded to the ceiling by the request schema, so they pass through unchanged.
    match body.limit:
        case None if api_context.user.may("general.ignore_hard_limit"):
            limit = None
        case None:
            limit = _MAX_NUMBER_OF_HOSTS
        case _:
            limit = body.limit

    return HostTable(api_context.config.sites, folders).list(
        limit=limit,
        query="" if isinstance(body.q, ApiOmitted) else body.q,
        sorters=DEFAULT_HOST_SORT if isinstance(body.sort, ApiOmitted) else body.sort,
        scoped_filter=(
            None
            if isinstance(body.filter, ApiOmitted)
            else _scope_and_check_sites(body.filter, api_context.config.sites)
        ),
        fields=_DEFAULT_FIELDS if isinstance(body.fields, ApiOmitted) else body.fields,
    )


def _scope_and_check_sites(node: FilterNode, site_configs: SiteConfigurations) -> SiteScopedFilter:
    try:
        return scope_filter_to_sites(node, frozenset(site_configs))
    except InvalidFilterError as exc:
        raise _invalid_filter(str(exc)) from exc


def scope_filter_to_sites(node: FilterNode, site_ids: Collection[SiteId]) -> SiteScopedFilter:
    try:
        scoped = scope_filter_by_site(node)
    except ValueError as exc:
        raise InvalidFilterError(str(exc)) from exc
    for site_id in sorted(scoped.sites or ()):
        if site_id not in site_ids:
            raise InvalidFilterError(f"Site {site_id!r} does not exist.")
    return scoped


def _invalid_filter(detail: str) -> RestAPIRequestGeneralException:
    return RestAPIRequestGeneralException(
        status=HTTPStatus.BAD_REQUEST, title="Invalid filter", detail=detail
    )


class HostTable:
    def __init__(
        self,
        site_configs: SiteConfigurations,
        folders: MonitorFolders,
        *,
        tag_groups: Set[str] = frozenset(),
    ) -> None:
        """``tag_groups`` are the IDs of the configured tag groups, which the dashboard filter for
        tags needs. A table without them reports that filter instead of applying it."""
        self._folders = folders
        self._tag_groups = tag_groups
        self._site_ids = frozenset(site_configs)
        self._customer_of = customer_resolver(sites=site_configs)
        self._sites = MonitorSites(
            MonitorSite(id=site_id, customer=self._customer_of(site_id)) for site_id in site_configs
        )

    def parse_filter(self, raw: str) -> SiteScopedFilter:
        try:
            node = FILTER_NODE.validate_json(raw)
        except ValueError as exc:
            raise InvalidFilterError(str(exc)) from exc
        return scope_filter_to_sites(node, self._site_ids)

    def list(
        self,
        *,
        limit: int | None,
        query: str,
        sorters: Sequence[HostSort],
        scoped_filter: SiteScopedFilter | None,
        fields: Set[HostOptionalField],
    ) -> HostsResponse:
        if scoped_filter is None:
            filters, site_ids = None, None
        else:
            filters, site_ids = scoped_filter.node, scoped_filter.site_scope(self._site_ids)

        host_repo = LiveStatusHostRepository(
            connection=sites.live(),
            folders=self._folders,
            sites=self._sites,
        )

        # NOTE: we never want this value scoped by the selected sites. It should always get full
        # count. As a temporary solution, we are querying count here and passing the result to the
        # handler. This is done to make the handler more testable without the need to be tested
        # within a request context as `sites` triggers that side-effect.
        total_host_count = host_repo.count_total()

        # `sites.only_sites([])` can't express "query zero sites"; an empty list is falsy to it and
        # gets treated as "no restriction" instead, i.e. every site. This happens when the filter
        # negates every currently configured site, so it's handled here before ever calling into
        # Livestatus, rather than being passed through.
        if site_ids == []:
            return HostsResponse(
                hosts=[],
                meta=HostsPageMeta(
                    limit=limit,
                    matched=0,
                    total=total_host_count,
                    fields=fields,
                    unreachable_sites=host_repo.unreachable_sites(),
                ),
            )

        # Like the total count above, and for the same reason: what a host is related to does not
        # change with the sites the reader has filtered the listing down to.
        visible_relations = host_repo.visible_relation_hosts(fields=fields, sorters=sorters)

        with sites.only_sites(site_ids):
            return _handle_list_hosts(
                host_repo,
                total_host_count,
                limit=limit,
                query=query,
                sorters=sorters,
                filters=(
                    HostFilter("")
                    if filters is None
                    else parse_as_livestatus_filter(filters, setup_folders=self._folders.titles)
                ),
                fields=fields,
                site_ids=site_ids,
                customer_of=self._customer_of,
                visible_relations=visible_relations,
            )

    def rows(
        self, *, columns: Sequence[str], sort: Sequence[str], limit: int, context: VisualContext
    ) -> TableRows[HostEntry]:
        translation = translate_filters(context, tag_groups=self._tag_groups)
        response = self.list(
            limit=limit,
            query="",
            sorters=HOST_TABLE.sorters(columns, sort),
            scoped_filter=translation.filter,
            fields=HOST_TABLE.fields(columns),
        )
        return TableRows(
            rows=response.hosts,
            matched=response.meta.matched,
            total=response.meta.total,
            unapplied_filters=translation.unapplied,
            unreachable_sites=response.meta.unreachable_sites,
        )


def _handle_list_hosts(
    host_repo: HostRepository,
    total_host_count: int,
    *,
    limit: int | None = _DEFAULT_LIMIT,
    query: str = "",
    sorters: Sequence[HostSort] = DEFAULT_HOST_SORT,
    filters: HostFilter = HostFilter(""),
    fields: Set[HostOptionalField] = _DEFAULT_FIELDS,
    site_ids: Sequence[SiteId] | None = None,
    customer_of: Callable[[str], str | None] = lambda _site_id: None,
    visible_relations: frozenset[tuple[str, str]] | None = None,
) -> HostsResponse:
    # Derived from the same `site_ids` the caller scoped the connection with via `only_sites`,
    # rather than taken as a separately-passed flag, so the two can't drift apart.
    has_site_filter = site_ids is not None

    hosts = host_repo.fetch(
        limit=limit,
        query=query,
        sorters=sorters,
        filters=filters,
        fields=fields,
        visible_relations=visible_relations,
    )
    # `limit` reaches Livestatus as a per-site cap (queried in parallel across sites, then merged
    # and sorted here), so a multi-site fetch can come back with up to `limit * len(sites)` rows.
    # Re-applying it client-side after the merge is what makes the *global* top-`limit` hold.
    if limit is not None:
        hosts = hosts[:limit]

    if limit is None:
        matched_host_count = len(hosts)
    elif query or filters or has_site_filter:
        matched_host_count = host_repo.count_matched(query=query, filters=filters, fields=fields)
    else:
        matched_host_count = total_host_count

    return HostsResponse(
        hosts=[HostEntry.from_domain(host, fields, customer_of(host.site_id)) for host in hosts],
        meta=HostsPageMeta(
            limit=limit,
            matched=matched_host_count,
            total=total_host_count,
            fields=fields,
            unreachable_sites=host_repo.unreachable_sites(),
        ),
    )


def make_endpoint_list_hosts(setup_folders: SetupFolderSource) -> VersionedEndpoint:
    """The endpoint listing hosts, titling their folders the way `setup_folders` reads them."""

    def list_hosts(
        api_context: ApiContext,
        body: HostsRequestBody = HostsRequestBody(),
    ) -> HostsResponse:
        """List hosts to be consumed by the all host monitoring page."""
        return _list_hosts(
            api_context,
            body,
            MonitorFolders(setup_folders(api_context.config, api_context.user)),
        )

    return VersionedEndpoint(
        metadata=EndpointMetadata(
            path="/monitor/hosts",
            link_relation="cmk/list",
            method="post",
        ),
        permissions=EndpointPermissions(
            # Declared for the permission tracker: inspected via user.may() during the request, but
            # none is required.
            required=permissions.Undocumented(
                permissions.AnyPerm(
                    [
                        permissions.OkayToIgnorePerm("general.see_all"),
                        permissions.OkayToIgnorePerm("bi.see_all"),
                        permissions.OkayToIgnorePerm("mkeventd.seeall"),
                        permissions.OkayToIgnorePerm("general.ignore_hard_limit"),
                        # Read while titling a folder, on an installation that keeps the folders a
                        # user may not read out of sight.
                        permissions.OkayToIgnorePerm("wato.see_all_folders"),
                    ]
                )
            )
        ),
        doc=EndpointDoc(family=MONITOR_HOSTS_FAMILY.name),
        behavior=EndpointBehavior(skip_locking=True, update_config_generation=False),
        versions={APIVersion.INTERNAL: EndpointHandler(handler=list_hosts)},
    )
