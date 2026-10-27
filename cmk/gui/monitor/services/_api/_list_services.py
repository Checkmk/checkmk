#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Sequence, Set
from http import HTTPStatus
from typing import Annotated, override, Self

from pydantic import PlainValidator

from cmk.ccc.site import SiteId
from cmk.gui import sites
from cmk.gui.monitor.hosts import customer_resolver
from cmk.gui.monitor.site_scope import MonitorSite, MonitorSites
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
from cmk.web.utils import permission_verification as permissions

from .._impl import LiveStatusServicesRepository
from .._models import (
    HostStateLabel,
    Service,
    ServiceFilter,
    ServiceOptionalField,
    ServiceSort,
    ServiceSortColumn,
    ServiceSortDirection,
)
from .._repositories import ServicesRepository
from ._family import MONITOR_SERVICES_FAMILY
from ._filters import parse_as_livestatus_filter, scope_filter_by_site, ServiceFilterNode
from ._limits import DEFAULT_SERVICE_LIMIT, resolve_service_limit
from ._list_host_services import HostServiceEntry, ServicesRequestBody
from ._validators import parse_service_search_query, parse_service_sort_options

_DEFAULT_SORT = (
    ServiceSort(column=ServiceSortColumn.HOST_NAME, direction=ServiceSortDirection.ASC),
    ServiceSort(column=ServiceSortColumn.NAME, direction=ServiceSortDirection.ASC),
)

_DEFAULT_FIELDS: frozenset[ServiceOptionalField] = frozenset()


@api_model
class ServiceEntry(HostServiceEntry):
    host_name: str = api_field(description="Name of the host the service runs on", example="web01")
    site_id: str = api_field(description="Site ID", example="local")
    host_state: HostStateLabel = api_field(
        description=(
            "State of the host the service runs on. 'PENDING' means the host has never been checked"
        ),
        example="UP",
    )

    @override
    @classmethod
    def from_domain(cls, service: Service) -> Self:
        return cls._from_domain(
            service,
            host_name=service.host_name,
            site_id=service.site_id,
            host_state=service.host_state_label,
        )


@api_model
class ServicesPageMeta:
    limit: int | None = api_field(description="Applied row limit.", example=1000)
    matched: int = api_field(description="Total matched services", example=42)
    total: int = api_field(description="Total number of services", example=1234)
    unreachable_sites: list[str] = api_field(
        description=(
            "IDs of the sites that could not be reached. Their services are missing from the "
            "services, 'matched' and 'total'."
        ),
        example=["remote_1"],
    )


@api_model
class ServicesResponse:
    services: list[ServiceEntry] = api_field(description="Services for this query", example=[])
    meta: ServicesPageMeta = api_field(description="Page metadata")


@api_model
class AllServicesRequestBody(ServicesRequestBody):
    sort: Annotated[
        list[ServiceSort] | ApiOmitted,
        PlainValidator(func=parse_service_sort_options, json_schema_input_type=list[str]),
    ] = api_field(
        description=(
            "Sort options. Each value is 'column:direction', e.g. 'host_name:asc'. "
            f"Allowed columns: {ServiceSortColumn.options()}. "
            f"Allowed directions: {ServiceSortDirection.options()}. "
            "Multiple values define a multi-column sort applied in the given order; a column must "
            "not be repeated. Omit to sort by host name, then service name."
        ),
        example="host_name:asc",
        default_factory=ApiOmitted,
    )
    q: Annotated[
        str | ApiOmitted,
        PlainValidator(func=parse_service_search_query, json_schema_input_type=str),
    ] = api_field(
        description=(
            "Search text, matched against the service name, its summary, the host name, the site, "
            "the customer and every text field asked for through `fields` (labels, tags, "
            "contacts, contact_groups, groups). Host name, site and customer are searched whether "
            "or not their column is shown. Omit or pass empty string to return all services."
        ),
        example="CPU",
        default_factory=ApiOmitted,
    )


def list_all_services(
    api_context: ApiContext,
    body: AllServicesRequestBody = AllServicesRequestBody(),
) -> ServicesResponse:
    """List the services of all hosts to be consumed by the all services monitoring page."""
    limit = resolve_service_limit(body.limit, api_context.user)

    all_site_ids = frozenset(api_context.config.sites)
    if isinstance(body.filter, ApiOmitted):
        filter_node, site_ids = None, None
    else:
        filter_node, site_ids = _scope_and_check_sites(body.filter, all_site_ids)

    customer_of = customer_resolver(sites=api_context.config.sites)
    services_repo = LiveStatusServicesRepository(
        connection=sites.live(),
        sites=MonitorSites(
            MonitorSite(id=site_id, customer=customer_of(site_id)) for site_id in all_site_ids
        ),
    )
    total_service_count = services_repo.count_total()

    # `sites.only_sites([])` can't express "query zero sites"; an empty list is falsy to it and gets
    # treated as "no restriction" instead, i.e. every site. This happens when the filter negates
    # every currently configured site, so it's handled here before ever calling into Livestatus.
    if site_ids == []:
        return ServicesResponse(
            services=[],
            meta=ServicesPageMeta(
                limit=limit,
                matched=0,
                total=total_service_count,
                unreachable_sites=services_repo.unreachable_sites(),
            ),
        )

    with sites.only_sites(site_ids):
        return _handle_list_all_services(
            services_repo,
            total_service_count,
            limit=limit,
            query="" if isinstance(body.q, ApiOmitted) else body.q,
            sorters=_DEFAULT_SORT if isinstance(body.sort, ApiOmitted) else body.sort,
            filters=(
                ServiceFilter("")
                if filter_node is None
                else parse_as_livestatus_filter(filter_node)
            ),
            fields=_DEFAULT_FIELDS if isinstance(body.fields, ApiOmitted) else body.fields,
            site_ids=site_ids,
        )


def _scope_and_check_sites(
    node: ServiceFilterNode, all_site_ids: frozenset[SiteId]
) -> tuple[ServiceFilterNode | None, list[SiteId] | None]:
    try:
        scoped = scope_filter_by_site(node)
    except ValueError as exc:
        raise _invalid_filter(str(exc)) from exc
    for site_id in sorted(scoped.sites or ()):
        if site_id not in all_site_ids:
            raise _invalid_filter(f"Site {site_id!r} does not exist.")
    return scoped.node, scoped.site_scope(all_site_ids)


def _invalid_filter(detail: str) -> RestAPIRequestGeneralException:
    return RestAPIRequestGeneralException(
        status=HTTPStatus.BAD_REQUEST, title="Invalid filter", detail=detail
    )


def _handle_list_all_services(
    services_repo: ServicesRepository,
    total_service_count: int,
    *,
    limit: int | None = DEFAULT_SERVICE_LIMIT,
    query: str = "",
    sorters: Sequence[ServiceSort] = _DEFAULT_SORT,
    filters: ServiceFilter = ServiceFilter(""),
    fields: Set[ServiceOptionalField] = _DEFAULT_FIELDS,
    site_ids: Sequence[SiteId] | None = None,
) -> ServicesResponse:
    services = services_repo.fetch(
        limit=limit, query=query, sorters=sorters, filters=filters, fields=fields
    )
    if limit is not None:
        services = services[:limit]

    if limit is None:
        matched_service_count = len(services)
    elif query or filters or site_ids is not None:
        matched_service_count = services_repo.count_matched(
            query=query, filters=filters, fields=fields
        )
    else:
        matched_service_count = total_service_count

    return ServicesResponse(
        services=[ServiceEntry.from_domain(service) for service in services],
        meta=ServicesPageMeta(
            limit=limit,
            matched=matched_service_count,
            total=total_service_count,
            unreachable_sites=services_repo.unreachable_sites(),
        ),
    )


ENDPOINT_LIST_ALL_SERVICES = VersionedEndpoint(
    metadata=EndpointMetadata(
        path="/monitor/services",
        link_relation=".../collection",
        method="post",
    ),
    permissions=EndpointPermissions(
        required=permissions.Undocumented(
            permissions.AnyPerm(
                [
                    permissions.OkayToIgnorePerm("general.see_all"),
                    permissions.OkayToIgnorePerm("bi.see_all"),
                    permissions.OkayToIgnorePerm("mkeventd.seeall"),
                    permissions.OkayToIgnorePerm("general.ignore_hard_limit"),
                    permissions.OkayToIgnorePerm("general.see_crash_reports"),
                    permissions.OkayToIgnorePerm("action.reschedule"),
                ]
            )
        )
    ),
    doc=EndpointDoc(family=MONITOR_SERVICES_FAMILY.name),
    behavior=EndpointBehavior(skip_locking=True, update_config_generation=False),
    versions={APIVersion.INTERNAL: EndpointHandler(handler=list_all_services)},
)
