#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Sequence
from typing import Annotated, Self

from annotated_types import Interval
from pydantic import PlainValidator

from cmk.gui import sites
from cmk.gui.logged_in import user
from cmk.gui.openapi.framework.api_config import APIVersion
from cmk.gui.openapi.framework.model import api_field, api_model, ApiOmitted
from cmk.gui.openapi.framework.versioned_endpoint import (
    EndpointBehavior,
    EndpointDoc,
    EndpointHandler,
    EndpointMetadata,
    EndpointPermissions,
    VersionedEndpoint,
)
from cmk.gui.utils import permission_verification as permissions

from .._impl import LiveStatusHostRepository
from .._models import (
    Host,
    HostFilter,
    HostSort,
    HostSortColumn,
    HostSortDirection,
    HostStateLabel,
)
from .._repositories import HostRepository
from ._family import MONITOR_HOSTS_FAMILY
from ._filters import FilterNode, parse_as_livestatus_filter
from ._modes import build_host_modes, ModeInfo
from ._validators import parse_host_search_query, parse_host_sort_options

# View-local limits, deliberately not coupled to the global soft/hard query limit settings so they
# never affect the legacy views.
_MIN_NUMBER_OF_HOSTS = 0
_MAX_NUMBER_OF_HOSTS = 5_000
_DEFAULT_LIMIT = 1_000

_DEFAULT_SORT = (HostSort(column=HostSortColumn.NAME, direction=HostSortDirection.ASC),)


@api_model
class HostEntry:
    name: str = api_field(description="Host name", example="web-server-01")
    state: HostStateLabel = api_field(description="Host state", example="UP")
    address: str = api_field(description="Primary IP address", example="10.0.0.1")
    alias: str = api_field(description="Host alias", example="Web Server")
    site_id: str = api_field(description="Site ID", example="local")
    num_services: int = api_field(description="Total number of services", example=48)
    num_services_ok: int = api_field(description="Number of services in OK state", example=42)
    num_services_warn: int = api_field(description="Number of services in WARNING state", example=3)
    num_services_crit: int = api_field(
        description="Number of services in CRITICAL state", example=1
    )
    num_services_unknown: int = api_field(
        description="Number of services in UNKNOWN state", example=0
    )
    num_services_pending: int = api_field(
        description="Number of services in PENDING state", example=2
    )
    modes: list[ModeInfo] | ApiOmitted = api_field(
        description=(
            "Active host modes (e.g. scheduled downtime, acknowledgement) rendered as linked "
            "icons. Empty when the host is in none of these modes."
        ),
        example=[],
        default_factory=ApiOmitted,
    )

    @classmethod
    def from_domain(cls, host: Host) -> Self:
        return cls(
            name=host.name,
            state=host.state_label,
            address=host.address,
            alias=host.alias,
            site_id=host.site_id,
            num_services=host.service_counts.total,
            num_services_ok=host.service_counts.ok,
            num_services_warn=host.service_counts.warn,
            num_services_crit=host.service_counts.crit,
            num_services_unknown=host.service_counts.unknown,
            num_services_pending=host.service_counts.pending,
            modes=build_host_modes(host),
        )


@api_model
class HostsPageMeta:
    limit: int = api_field(
        description="Applied row limit. 0 means no limit was applied (unlimited).",
        example=1000,
    )
    matched: int = api_field(description="Total matched hosts", example=42)
    total: int = api_field(description="Total number of hosts", example=1234)


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
        description="Filter hosts by name, alias, or IP. Omit or pass empty string to return all hosts.",
        example="web-server",
        default_factory=ApiOmitted,
    )
    filter: FilterNode | ApiOmitted = api_field(
        description="Boolean filter expression tree. Omit to return all hosts.",
        default_factory=ApiOmitted,
    )


def list_hosts(body: HostsRequestBody = HostsRequestBody()) -> HostsResponse:
    """List hosts to be consumed by the all host monitoring page."""
    host_repo = LiveStatusHostRepository(connection=sites.live())

    parsed_filters = (
        HostFilter("")
        if isinstance(body.filter, ApiOmitted)
        else parse_as_livestatus_filter(body.filter)
    )

    return _handle_list_hosts(
        host_repo,
        limit=_resolve_limit(body.limit, may_remove_limit=user.may("general.ignore_hard_limit")),
        query="" if isinstance(body.q, ApiOmitted) else body.q,
        sorters=_DEFAULT_SORT if isinstance(body.sort, ApiOmitted) else body.sort,
        filters=parsed_filters,
    )


def _resolve_limit(requested: int | None, *, may_remove_limit: bool) -> int | None:
    """Resolve the requested row limit into the one to actually apply.

    A ``None`` request means "remove the limit". We only honor that for users allowed to ignore the
    hard limit; everyone else is clamped to the safety ceiling. Numeric requests are already bounded
    to the ceiling by the request schema, so they pass through unchanged.
    """
    if requested is None:
        return None if may_remove_limit else _MAX_NUMBER_OF_HOSTS
    return requested


def _handle_list_hosts(
    host_repo: HostRepository,
    *,
    limit: int | None = _DEFAULT_LIMIT,
    query: str = "",
    sorters: Sequence[HostSort] = _DEFAULT_SORT,
    filters: HostFilter = HostFilter(""),
) -> HostsResponse:
    hosts = host_repo.fetch(
        limit=limit,
        query=query,
        sorters=sorters,
        filters=filters,
    )
    total_host_count = host_repo.count_total()
    if limit is None:
        matched_host_count = len(hosts)
    elif query or filters:
        matched_host_count = host_repo.count_matched(query=query, filters=filters)
    else:
        matched_host_count = total_host_count

    return HostsResponse(
        hosts=[HostEntry.from_domain(host) for host in hosts],
        meta=HostsPageMeta(
            limit=limit if limit is not None else 0,
            matched=matched_host_count,
            total=total_host_count,
        ),
    )


ENDPOINT_LIST_HOSTS = VersionedEndpoint(
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
                ]
            )
        )
    ),
    doc=EndpointDoc(family=MONITOR_HOSTS_FAMILY.name),
    behavior=EndpointBehavior(skip_locking=True),
    versions={APIVersion.INTERNAL: EndpointHandler(handler=list_hosts)},
)
