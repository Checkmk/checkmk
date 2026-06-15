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
from ._validators import parse_host_search_query, parse_host_sort_options

# NOTE: currently hardcoding these constraints. It's to be determined where these should come from,
# e.g. global settings.
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
        )


@api_model
class HostsPageMeta:
    limit: int = api_field(description="Requested page size", example=1000)
    total: int = api_field(description="Total number of hosts", example=1234)


@api_model
class HostsResponse:
    hosts: list[HostEntry] = api_field(description="The hosts for this query", example=[])
    meta: HostsPageMeta = api_field(description="Page metadata")


@api_model
class HostsRequestBody:
    limit: Annotated[int, Interval(ge=_MIN_NUMBER_OF_HOSTS, le=_MAX_NUMBER_OF_HOSTS)] = api_field(
        description="Number of hosts to return",
        example=_DEFAULT_LIMIT,
        default=_DEFAULT_LIMIT,
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
    user.need_permission("general.see_all")

    host_repo = LiveStatusHostRepository(connection=sites.live())

    parsed_filters = (
        HostFilter("")
        if isinstance(body.filter, ApiOmitted)
        else parse_as_livestatus_filter(body.filter)
    )

    return _handle_list_hosts(
        host_repo,
        limit=body.limit,
        search_query="" if isinstance(body.q, ApiOmitted) else body.q,
        sorters=_DEFAULT_SORT if isinstance(body.sort, ApiOmitted) else body.sort,
        filters=parsed_filters,
    )


def _handle_list_hosts(
    host_repo: HostRepository,
    *,
    limit: int,
    search_query: str = "",
    sorters: Sequence[HostSort] = _DEFAULT_SORT,
    filters: HostFilter = HostFilter(""),
) -> HostsResponse:
    hosts = host_repo.fetch(
        limit=limit,
        search_query=search_query,
        sorters=sorters,
        filters=filters,
    )
    host_total = host_repo.count(search_query=search_query, filters=filters)

    return HostsResponse(
        hosts=[HostEntry.from_domain(host) for host in hosts],
        meta=HostsPageMeta(limit=limit, total=host_total),
    )


ENDPOINT_LIST_HOSTS = VersionedEndpoint(
    metadata=EndpointMetadata(
        path="/monitor/hosts",
        link_relation="cmk/list",
        method="post",
    ),
    permissions=EndpointPermissions(
        required=permissions.Undocumented(
            permissions.AnyPerm(
                [
                    permissions.Perm("general.see_all"),
                    # NOTE: these two need to be included in order to make the REST API framework
                    # happy. The "see_all" permission is the only one that is required to check.
                    permissions.OkayToIgnorePerm("bi.see_all"),
                    permissions.OkayToIgnorePerm("mkeventd.seeall"),
                ]
            )
        )
    ),
    doc=EndpointDoc(family=MONITOR_HOSTS_FAMILY.name),
    versions={APIVersion.INTERNAL: EndpointHandler(handler=list_hosts)},
)
