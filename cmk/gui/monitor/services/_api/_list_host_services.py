#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import datetime as dt
from typing import Annotated, Self

from annotated_types import Interval

from cmk.ccc.site import SiteId
from cmk.gui import sites
from cmk.gui.logged_in import user
from cmk.gui.openapi.framework._types import PathParam, QueryParam
from cmk.gui.openapi.framework.api_config import APIVersion
from cmk.gui.openapi.framework.model import api_field, api_model
from cmk.gui.openapi.framework.model.common_fields import AnnotatedHostName
from cmk.gui.openapi.framework.model.converter import SiteIdConverter, TypedPlainValidator
from cmk.gui.openapi.framework.versioned_endpoint import (
    EndpointBehavior,
    EndpointDoc,
    EndpointHandler,
    EndpointMetadata,
    EndpointPermissions,
    VersionedEndpoint,
)
from cmk.gui.openapi.utils import ProblemException
from cmk.gui.utils import permission_verification as permissions

from .._impl import LiveStatusHostServicesRepository
from .._models import Service, ServiceStateLabel
from .._repositories import HostServicesRepository
from ._family import MONITOR_SERVICES_FAMILY

# View-local limits, deliberately not coupled to the global soft/hard query limit settings so they
# never affect the legacy views.
_MIN_HOST_SVC_LIMIT = 0
_MAX_HOST_SVC_LIMIT = 5_000
_DEFAULT_LIMIT = 1_000


@api_model
class HostServiceEntry:
    name: str = api_field(description="Service name", example="Check_MK HW/SW Inventory")
    state: ServiceStateLabel = api_field(description="Service state", example="OK")
    summary: str = api_field(
        description="Service summary",
        example="Found no data, execution time 0.0 sec",
    )
    last_check: dt.datetime = api_field(
        description="Timestamp of the host's last check",
        example="2026-07-13T11:38:30Z",
    )
    last_state_change: dt.datetime = api_field(
        description="Timestamp of the host's last state change",
        example="2026-07-13T11:39:00Z",
    )

    @classmethod
    def from_domain(cls, service: Service) -> Self:
        return cls(
            name=service.name,
            state=service.state_label,
            summary=service.summary,
            last_check=service.last_check,
            last_state_change=service.last_state_change,
        )


@api_model
class HostServicesPageMeta:
    hostname: str = api_field(description="Host name", example="web-server-01")
    site_id: str = api_field(description="Site ID", example="local")
    limit: int | None = api_field(description="Applied row limit.", example=1000)
    matched: int = api_field(description="Total matched services", example=1234)
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


def list_services(
    hostname: Annotated[
        AnnotatedHostName,
        PathParam(description="Host name", example="web-server-01"),
    ],
    site_id: Annotated[
        Annotated[SiteId, TypedPlainValidator(str, SiteIdConverter.should_exist)],
        QueryParam(description="An existing site id", example="local"),
    ],
    body: ServicesRequestBody,
) -> HostServicesResponse:
    """List services of a host to be consumed by the host services monitoring page."""
    with sites.only_sites(site_id):
        host_services_repo = LiveStatusHostServicesRepository(connection=sites.live())

        # A `None` request means "remove the limit". We only honor that for users allowed to ignore
        # the hard limit; everyone else is clamped to the safety ceiling. Numeric requests are
        # already bounded to the ceiling by the request schema, so they pass through unchanged.
        match body.limit:
            case None if user.may("general.ignore_hard_limit"):
                limit = None
            case None:
                limit = _MAX_HOST_SVC_LIMIT
            case _:
                limit = body.limit

        return _handle_list_services(
            host_services_repo,
            hostname=hostname,
            site_id=site_id,
            limit=limit,
        )


def _handle_list_services(
    host_services_repo: HostServicesRepository,
    *,
    hostname: str,
    site_id: str,
    limit: int | None = _DEFAULT_LIMIT,
) -> HostServicesResponse:
    if not host_services_repo.host_exists(hostname):
        raise ProblemException(
            status=404,
            title="The requested host was not found",
            detail=f"The host {hostname!r} was not found on site {site_id!r}",
        ) from None

    services = host_services_repo.fetch(hostname, limit=limit)
    total_service_count = host_services_repo.count_total(hostname)

    return HostServicesResponse(
        services=[HostServiceEntry.from_domain(service) for service in services],
        meta=HostServicesPageMeta(
            hostname=hostname,
            site_id=site_id,
            limit=limit,
            matched=total_service_count,
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
