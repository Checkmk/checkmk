#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Sequence, Set
from typing import Annotated, Self

from annotated_types import Interval
from pydantic import PlainValidator

from cmk.ccc.site import SiteId
from cmk.gui import sites
from cmk.gui.openapi.framework import (
    ApiContext,
    APIVersion,
    EndpointBehavior,
    EndpointDoc,
    EndpointHandler,
    EndpointMetadata,
    EndpointPermissions,
    PathParam,
    QueryParam,
    VersionedEndpoint,
)
from cmk.gui.openapi.framework.model import api_field, api_model, ApiOmitted
from cmk.gui.openapi.framework.model.common_fields import AnnotatedHostName
from cmk.gui.openapi.framework.model.converter import SiteIdConverter, TypedPlainValidator
from cmk.gui.openapi.utils import ProblemException
from cmk.web.utils import permission_verification as permissions

from .._impl import LiveStatusHostServicesRepository
from .._models import (
    Service,
    ServiceFilter,
    ServiceLabelValue,
    ServiceOptionalField,
    ServiceSort,
    ServiceSortColumn,
    ServiceSortDirection,
    ServiceStateLabel,
    UnixTimestamp,
)
from .._repositories import HostServicesRepository
from ._family import MONITOR_SERVICES_FAMILY
from ._filters import parse_as_livestatus_filter, ServiceFilterNode
from ._modes import build_service_modes_by_id, ServiceModeInfo
from ._perfometer import ServicePerfometer
from ._validators import parse_service_search_query, parse_service_sort_options

# View-local limits, deliberately not coupled to the global soft/hard query limit settings so they
# never affect the legacy views.
_MIN_HOST_SVC_LIMIT = 0
_MAX_HOST_SVC_LIMIT = 5_000
_DEFAULT_LIMIT = 1_000

# Requesting no sorter is not the same as requesting no order: the repository reads an empty list
# as "the page default", which leads with Checkmk's own services.
_DEFAULT_SORT: tuple[ServiceSort, ...] = ()

# The page's default columns; everything else has to be asked for.
_DEFAULT_FIELDS: frozenset[ServiceOptionalField] = frozenset()


@api_model
class HostServiceEntry:
    name: str = api_field(description="Service name", example="Check_MK HW/SW Inventory")
    state: ServiceStateLabel = api_field(description="Service state", example="OK")
    is_flapping: bool = api_field(
        description="Whether the service state is flapping", example=False
    )
    stale: bool = api_field(
        description="Whether the service hasn't been checked recently enough", example=False
    )
    summary: str = api_field(
        description="Service summary",
        example="Found no data, execution time 0.0 sec",
    )
    last_check: UnixTimestamp | None = api_field(
        description=(
            "Unix timestamp of the service's last check. Null for services that have never been "
            "checked, i.e. those still pending their first check."
        ),
        example=1752405510,
    )
    last_state_change: UnixTimestamp = api_field(
        description="Unix timestamp of the service's last state change",
        example=1752405540,
    )
    modes: list[ServiceModeInfo] | ApiOmitted = api_field(
        description=(
            "Active service modes (e.g. scheduled downtime, acknowledgement) rendered as linked "
            "icons. Empty when the service is in none of these modes."
        ),
        example=[],
        default_factory=ApiOmitted,
    )
    labels: dict[str, ServiceLabelValue] | ApiOmitted = api_field(
        description="Service labels, keyed by label name. Omitted when the service has none.",
        example={"cmk/check_plugin": ServiceLabelValue(value="cpu_load", source="discovered")},
        default_factory=ApiOmitted,
    )
    tags: dict[str, str] | ApiOmitted = api_field(
        description="Service tags, keyed by tag group. Omitted when the service has none.",
        example={"criticality": "prod"},
        default_factory=ApiOmitted,
    )
    contacts: list[str] | ApiOmitted = api_field(
        description="Contacts responsible for this service. Omitted when it has none.",
        example=["hh"],
        default_factory=ApiOmitted,
    )
    contact_groups: list[str] | ApiOmitted = api_field(
        description="Contact groups this service is in. Omitted when it is in none.",
        example=["all"],
        default_factory=ApiOmitted,
    )
    perfometer: ServicePerfometer | ApiOmitted = api_field(
        description=(
            "Perf-O-Meter of the service's performance data. Omitted when the service reports no "
            "performance data or none of it matches a Perf-O-Meter definition."
        ),
        default_factory=ApiOmitted,
    )

    @classmethod
    def from_domain(cls, service: Service, *, hostname: str, site_id: str) -> Self:
        return cls(
            name=service.name,
            state=service.state_label,
            is_flapping=service.is_flapping,
            stale=service.stale,
            summary=service.summary,
            last_check=service.last_check,
            last_state_change=service.last_state_change,
            modes=build_service_modes_by_id(service, hostname=hostname, site_id=site_id)
            or ApiOmitted(),
            labels=service.labels if service.labels is not None else ApiOmitted(),
            tags=service.tags if service.tags is not None else ApiOmitted(),
            contacts=service.contacts if service.contacts is not None else ApiOmitted(),
            contact_groups=service.contact_groups
            if service.contact_groups is not None
            else ApiOmitted(),
            perfometer=ServicePerfometer.from_perf_data(service.perf_data, service.check_command)
            or ApiOmitted(),
        )


@api_model
class HostServicesPageMeta:
    hostname: str = api_field(description="Host name", example="web-server-01")
    site_id: str = api_field(description="Site ID", example="local")
    limit: int | None = api_field(description="Applied row limit.", example=1000)
    matched: int = api_field(description="Total matched services", example=42)
    total: int = api_field(description="Total number of services", example=1234)


@api_model
class HostServicesResponse:
    services: list[HostServiceEntry] = api_field(description="Services for this query", example=[])
    meta: HostServicesPageMeta = api_field(description="Page metadata")


@api_model
class ServicesRequestBody:
    limit: Annotated[int, Interval(ge=_MIN_HOST_SVC_LIMIT, le=_MAX_HOST_SVC_LIMIT)] | None = (
        api_field(
            description=(
                "Number of services to return. Pass null to remove the limit entirely; this requires "
                "the 'general.ignore_hard_limit' permission and otherwise falls back to the maximum "
                f"of {_MAX_HOST_SVC_LIMIT}."
            ),
            example=_DEFAULT_LIMIT,
            default=_DEFAULT_LIMIT,
        )
    )
    sort: Annotated[
        list[ServiceSort] | ApiOmitted,
        PlainValidator(func=parse_service_sort_options, json_schema_input_type=list[str]),
    ] = api_field(
        description=(
            "Sort options. Each value is 'column:direction', e.g. 'name:asc'. "
            f"Allowed columns: {ServiceSortColumn.options()}. "
            f"Allowed directions: {ServiceSortDirection.options()}. "
            "Multiple values define a multi-column sort applied in the given order; a column must "
            "not be repeated."
        ),
        example="name:asc",
        default_factory=ApiOmitted,
    )
    q: Annotated[
        str | ApiOmitted,
        PlainValidator(func=parse_service_search_query, json_schema_input_type=str),
    ] = api_field(
        description=(
            "Search text, matched against the service name and its summary. Omit or pass empty "
            "string to return all services."
        ),
        example="CPU",
        default_factory=ApiOmitted,
    )
    filter: ServiceFilterNode | ApiOmitted = api_field(
        description="Boolean filter expression tree. Omit to return all services.",
        default_factory=ApiOmitted,
    )
    fields: frozenset[ServiceOptionalField] | ApiOmitted = api_field(
        description=(
            f"Optional field names to include. Allowed values: {ServiceOptionalField.options()}. "
            "Each one costs a livestatus column per service, so only ask for the ones a visible "
            "column needs. Omit to return the default fields only."
        ),
        example=["labels"],
        default_factory=ApiOmitted,
    )


def list_services(
    hostname: Annotated[
        AnnotatedHostName,
        PathParam(description="Host name", example="web-server-01"),
    ],
    site_id: Annotated[
        Annotated[SiteId, TypedPlainValidator(str, SiteIdConverter.should_exist)],
        QueryParam(description="An existing site id", example="local"),
    ],
    api_context: ApiContext,
    body: ServicesRequestBody = ServicesRequestBody(),
) -> HostServicesResponse:
    """List services of a host to be consumed by the host services monitoring page."""
    with sites.only_sites(site_id):
        host_services_repo = LiveStatusHostServicesRepository(connection=sites.live())

        # A `None` request means "remove the limit". We only honor that for users allowed to ignore
        # the hard limit; everyone else is clamped to the safety ceiling. Numeric requests are
        # already bounded to the ceiling by the request schema, so they pass through unchanged.
        match body.limit:
            case None if api_context.user.may("general.ignore_hard_limit"):
                limit = None
            case None:
                limit = _MAX_HOST_SVC_LIMIT
            case _:
                limit = body.limit

        parsed_filters = (
            ServiceFilter("")
            if isinstance(body.filter, ApiOmitted)
            else parse_as_livestatus_filter(body.filter)
        )

        return _handle_list_services(
            host_services_repo,
            hostname=hostname,
            site_id=site_id,
            limit=limit,
            query="" if isinstance(body.q, ApiOmitted) else body.q,
            sorters=_DEFAULT_SORT if isinstance(body.sort, ApiOmitted) else body.sort,
            filters=parsed_filters,
            fields=_DEFAULT_FIELDS if isinstance(body.fields, ApiOmitted) else body.fields,
        )


def _handle_list_services(
    host_services_repo: HostServicesRepository,
    *,
    hostname: str,
    site_id: str,
    limit: int | None = _DEFAULT_LIMIT,
    query: str = "",
    sorters: Sequence[ServiceSort] = _DEFAULT_SORT,
    filters: ServiceFilter = ServiceFilter(""),
    fields: Set[ServiceOptionalField] = _DEFAULT_FIELDS,
) -> HostServicesResponse:
    if not host_services_repo.host_exists(hostname):
        raise ProblemException(
            status=404,
            title="The requested host was not found",
            detail=f"The host {hostname!r} was not found on site {site_id!r}",
        ) from None

    services = host_services_repo.fetch(
        hostname, limit=limit, query=query, sorters=sorters, filters=filters, fields=fields
    )
    total_service_count = host_services_repo.count_total(hostname)
    if limit is None:
        matched_service_count = len(services)
    elif query or filters:
        matched_service_count = host_services_repo.count_matched(
            hostname, query=query, filters=filters
        )
    else:
        matched_service_count = total_service_count

    return HostServicesResponse(
        services=[
            HostServiceEntry.from_domain(service, hostname=hostname, site_id=site_id)
            for service in services
        ],
        meta=HostServicesPageMeta(
            hostname=hostname,
            site_id=site_id,
            limit=limit,
            matched=matched_service_count,
            total=total_service_count,
        ),
    )


ENDPOINT_LIST_HOST_SERVICES = VersionedEndpoint(
    metadata=EndpointMetadata(
        path="/monitor/hosts/{hostname}/services",
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
    doc=EndpointDoc(family=MONITOR_SERVICES_FAMILY.name),
    behavior=EndpointBehavior(skip_locking=True),
    versions={APIVersion.INTERNAL: EndpointHandler(handler=list_services)},
)
