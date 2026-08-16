#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Annotated, Self

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
from cmk.gui.openapi.framework.model import api_field, api_model
from cmk.gui.openapi.framework.model.common_fields import AnnotatedHostName
from cmk.gui.openapi.framework.model.converter import SiteIdConverter, TypedPlainValidator
from cmk.gui.openapi.utils import ProblemException
from cmk.gui.utils import permission_verification as permissions

from .._exceptions import ServiceNotFoundError
from .._impl import LiveStatusHostServicesRepository
from .._models import (
    HostStateLabel,
    ServiceLabelValue,
    ServiceOverview,
    ServiceStateLabel,
    UnixTimestamp,
)
from .._repositories import HostServicesRepository
from ._family import MONITOR_SERVICES_FAMILY
from ._modes import build_host_modes, build_service_modes, ServiceModeInfo
from ._urls import host_view_link, service_parameters_link, service_view_link


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
    host_alias: str = api_field(description="Alias of the host", example="Web Server")
    host_state: HostStateLabel = api_field(description="State of the host", example="UP")
    host_modes: list[ServiceModeInfo] = api_field(
        description=(
            "Active modes of the host the service runs on, rendered as linked icons next to its "
            "state. Empty when the host is in none of these modes."
        ),
        example=[],
    )
    legacy_host_status_link: str = api_field(
        description="URL to the legacy host status view",
        example="view.py?view_name=hoststatus&site=local&host=web-server-01",
    )
    legacy_service_status_link: str = api_field(
        description="URL to the legacy service detail view",
        example="view.py?view_name=service&site=local&host=web-server-01&service=CPU+utilization",
    )
    legacy_service_parameters_link: str | None = api_field(
        description=(
            "URL to the Setup page listing the parameters of this service. Null for users who may "
            "not see rulesets."
        ),
        example="wato.py?mode=object_parameters&host=web-server-01&service=CPU+utilization",
    )
    contact_groups: list[str] = api_field(
        description="Contact groups responsible for this service",
        example=["all"],
    )
    summary: str = api_field(
        description="Service summary, i.e. the first line of the check plugin output",
        example="OK - load average: 0.10, 0.05, 0.01",
    )
    long_output: str = api_field(
        description=(
            "The remaining check plugin output below the summary. Empty when the plugin produces "
            "no details. Can span many lines, so the frontend renders it collapsed."
        ),
        example="15 min load: 0.01 (per core: 0.01)",
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
    current_attempt: int = api_field(description="The current check attempt", example=2)
    max_check_attempts: int = api_field(
        description="Number of attempts after which a problem turns hard", example=4
    )
    next_check: UnixTimestamp | None = api_field(
        description=(
            "Unix timestamp of the next scheduled check. Null for passive services, which are "
            "never scheduled."
        ),
        example=1752405600,
    )
    tags: dict[str, str] = api_field(
        description="Service tags",
        example={"criticality": "prod"},
    )
    labels: dict[str, ServiceLabelValue] = api_field(
        description="Service labels",
        example={"cmk/check_plugin": ServiceLabelValue(value="cpu_load", source="discovered")},
    )

    @classmethod
    def from_domain(cls, service: ServiceOverview, *, may_see_parameters: bool) -> Self:
        def read[T](value: T | None, name: str) -> T:
            """The overview reads every column, so a missing one is a bug, not an omission."""
            if value is None:
                raise ValueError(f"service overview is missing {name!r}")
            return value

        return cls(
            name=service.name,
            host_name=service.host_name,
            site_id=service.site_id,
            state=service.state_label,
            modes=build_service_modes(service),
            host_alias=service.host_alias,
            host_state=service.host_state_label,
            host_modes=build_host_modes(service),
            legacy_host_status_link=host_view_link("hoststatus", service),
            legacy_service_status_link=service_view_link("service", service),
            legacy_service_parameters_link=(
                service_parameters_link(service) if may_see_parameters else None
            ),
            contact_groups=read(service.contact_groups, "contact_groups"),
            summary=service.summary,
            long_output=service.long_output,
            last_check=service.last_check,
            last_state_change=service.last_state_change,
            current_attempt=service.current_attempt,
            max_check_attempts=service.max_check_attempts,
            next_check=service.next_check,
            tags=read(service.tags, "tags"),
            labels=read(service.labels, "labels"),
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
    api_context: ApiContext,
) -> ServiceOverviewResponse:
    """Show the overview for a single service of a host."""
    with sites.only_sites(site_id):
        host_services_repo = LiveStatusHostServicesRepository(connection=sites.live())

        return _handle_get_service_overview(
            host_services_repo,
            hostname=hostname,
            service_name=service_name,
            site_id=site_id,
            may_see_parameters=api_context.user.may("wato.rulesets"),
        )


def _handle_get_service_overview(
    host_services_repo: HostServicesRepository,
    *,
    hostname: str,
    service_name: str,
    site_id: str,
    may_see_parameters: bool = False,
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

    return ServiceOverviewResponse.from_domain(service, may_see_parameters=may_see_parameters)


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
                    permissions.OkayToIgnorePerm("wato.rulesets"),
                ]
            )
        )
    ),
    doc=EndpointDoc(family=MONITOR_SERVICES_FAMILY.name),
    behavior=EndpointBehavior(skip_locking=True),
    versions={APIVersion.INTERNAL: EndpointHandler(handler=get_service_overview)},
)
