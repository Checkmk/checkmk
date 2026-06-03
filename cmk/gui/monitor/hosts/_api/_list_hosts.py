#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Annotated, Self

from annotated_types import Interval
from pydantic import PlainValidator

from cmk.gui import sites
from cmk.gui.logged_in import user
from cmk.gui.monitor.hosts._impl import LiveStatusHostRepository
from cmk.gui.monitor.hosts._models import (
    Host,
    HostSort,
    HostSortColumn,
    HostSortDirection,
    StateLabel,
)
from cmk.gui.monitor.hosts._repositories import HostRepository
from cmk.gui.openapi.framework import QueryParam
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

from ._family import MONITOR_HOSTS_FAMILY
from ._validators import parse_host_sort_options

# NOTE: currently hardcoding these constraints. It's to be determined where these should come from,
# e.g. global settings.
_MIN_NUMBER_OF_HOSTS = 0
_MAX_NUMBER_OF_HOSTS = 5_000


@api_model
class HostEntry:
    name: str = api_field(description="Host name", example="web-server-01")
    state: StateLabel = api_field(description="Host state", example="UP")
    ip: str = api_field(description="Primary IP address", example="10.0.0.1")
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
            ip=host.ip,
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


type Limit = Annotated[
    int,
    Interval(ge=_MIN_NUMBER_OF_HOSTS, le=_MAX_NUMBER_OF_HOSTS),
    QueryParam(description="Number of hosts to return", example="1000"),
]


type Sort = Annotated[
    list[HostSort] | ApiOmitted,
    PlainValidator(func=parse_host_sort_options, json_schema_input_type=list[str]),
    QueryParam(
        description=(
            "Repeated sort param. Each value is 'column:direction', e.g. 'name:asc'. "
            f"Allowed columns: {HostSortColumn.options()}. "
            f"Allowed directions: {HostSortDirection.options()}. "
            "Multiple values define a multi-column sort applied in the given order; a column must "
            "not be repeated. For example, 'sort=name:asc&sort=num_services:desc' sorts by name "
            "ascending and then by number of services descending."
        ),
        example="name:asc",
        is_list=True,
    ),
]


def list_hosts(limit: Limit = 1000, sort: Sort = ApiOmitted()) -> HostsResponse:
    """List hosts to be consumed by the all host monitoring page."""
    user.need_permission("general.see_all")

    # ``sort`` is validated to expose the parameter in the API spec; applying it is done by the
    # host handlers and wired up there separately.
    host_repo = LiveStatusHostRepository(connection=sites.live())

    return _handle_list_hosts(host_repo, limit=limit)


def _handle_list_hosts(host_repo: HostRepository, *, limit: int) -> HostsResponse:
    hosts = host_repo.fetch(limit=limit)
    host_total = host_repo.count()

    return HostsResponse(
        hosts=[HostEntry.from_domain(host) for host in hosts],
        meta=HostsPageMeta(limit=limit, total=host_total),
    )


ENDPOINT_LIST_HOSTS = VersionedEndpoint(
    metadata=EndpointMetadata(
        path="/monitor/hosts",
        link_relation="cmk/list",
        method="get",
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
