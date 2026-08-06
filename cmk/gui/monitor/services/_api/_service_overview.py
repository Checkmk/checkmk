#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Annotated, Self

from cmk.ccc.site import SiteId
from cmk.gui import sites
from cmk.gui.openapi.framework import (
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
from cmk.gui.openapi.framework.model import api_field, api_model
from cmk.gui.openapi.framework.model.common_fields import AnnotatedHostName
from cmk.gui.openapi.framework.model.converter import SiteIdConverter, TypedPlainValidator
from cmk.gui.openapi.utils import ProblemException
from cmk.gui.utils import permission_verification as permissions

from .._exceptions import ServiceNotFoundError
from .._impl import LiveStatusHostServicesRepository
from .._models import ServiceOverview, ServiceStateLabel
from .._repositories import HostServicesRepository
from ._family import MONITOR_SERVICES_FAMILY
from ._modes import build_service_modes, ServiceModeInfo


@api_model
class ServiceOverviewResponse:
    name: str = api_field(description="Service name", example="CPU utilization")
    host_name: str = api_field(
        description="Name of the host this service belongs to", example="web-server-01"
    )
    site_id: str = api_field(description="Site ID", example="local")
    state: ServiceStateLabel = api_field(description="Service state", example="OK")
    modes: list[ServiceModeInfo] = api_field(
        description=(
            "Active service modes (e.g. scheduled downtime, acknowledgement, disabled "
            "notifications) rendered as linked icons. Empty when the service is in none of these "
            "modes."
        ),
        example=[],
    )

    @classmethod
    def from_domain(cls, service: ServiceOverview) -> Self:
        return cls(
            name=service.name,
            host_name=service.host_name,
            site_id=service.site_id,
            state=service.state_label,
            modes=build_service_modes(service),
        )


def get_service_overview(
    hostname: Annotated[
        AnnotatedHostName,
        PathParam(description="Host name", example="web-server-01"),
    ],
    site_id: Annotated[
        Annotated[SiteId, TypedPlainValidator(str, SiteIdConverter.should_exist)],
        QueryParam(description="An existing site id", example="local"),
    ],
    service_name: Annotated[
        str,
        QueryParam(description="The service name", example="CPU utilization"),
    ],
) -> ServiceOverviewResponse:
    """Show the overview for a single service of a host."""
    with sites.only_sites(site_id):
        host_services_repo = LiveStatusHostServicesRepository(connection=sites.live())

        return _handle_get_service_overview(
            host_services_repo,
            hostname=hostname,
            service_name=service_name,
            site_id=site_id,
        )


def _handle_get_service_overview(
    host_services_repo: HostServicesRepository,
    *,
    hostname: str,
    service_name: str,
    site_id: str,
) -> ServiceOverviewResponse:
    try:
        service = host_services_repo.get_overview(
            hostname=hostname, service_name=service_name, site_id=site_id
        )
    except ServiceNotFoundError:
        raise ProblemException(
            status=404,
            title="The requested service was not found",
            detail=(
                f"The service {service_name!r} of host {hostname!r} was not found on site "
                f"{site_id!r}"
            ),
        ) from None

    return ServiceOverviewResponse.from_domain(service)


ENDPOINT_GET_SERVICE_OVERVIEW = VersionedEndpoint(
    metadata=EndpointMetadata(
        path="/monitor/hosts/{hostname}/service",
        link_relation="cmk/show",
        method="get",
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
                ]
            )
        )
    ),
    doc=EndpointDoc(family=MONITOR_SERVICES_FAMILY.name),
    behavior=EndpointBehavior(skip_locking=True),
    versions={APIVersion.INTERNAL: EndpointHandler(handler=get_service_overview)},
)
