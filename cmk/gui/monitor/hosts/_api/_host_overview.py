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
from cmk.web.utils import permission_verification as permissions

from .._customer import customer_resolver
from .._exceptions import HostNotFoundError
from .._impl import LiveStatusHostRepository
from .._models import (
    Host,
    HostLabelValue,
    HostStateLabel,
    ServiceCounts,
    UnixTimestamp,
)
from .._repositories import HostRepository
from ._family import MONITOR_HOSTS_FAMILY
from ._modes import build_host_modes, ModeInfo
from ._urls import host_view_link


@api_model
class HostOverviewResponse:
    name: str = api_field(description="Host name", example="web-server-01")
    state: HostStateLabel = api_field(description="Host state", example="UP")
    address: str = api_field(description="Primary IP address", example="10.0.0.1")
    alias: str = api_field(description="Host alias", example="Web Server")
    site_id: str = api_field(description="Site ID", example="local")
    site_alias: str = api_field(description="Site alias", example="Local site")
    service_counts: ServiceCounts = api_field(
        description="Service counts",
        example=ServiceCounts(total=48, ok=42, warn=3, crit=1, unknown=0, pending=2),
    )
    modes: list[ModeInfo] = api_field(
        description=(
            "Active host modes (e.g. scheduled downtime, acknowledgement) rendered as linked "
            "icons. Empty when the host is in none of these modes."
        ),
        example=[],
    )
    last_check: UnixTimestamp = api_field(
        description="Unix timestamp of the host's last check",
        example=1752405510,
    )
    last_state_change: UnixTimestamp = api_field(
        description="Unix timestamp of the host's last state change",
        example=1752405540,
    )
    customer: str | None = api_field(
        description=(
            "Name of the customer the host belongs to, which is the customer of the site "
            "monitoring it. Null on editions without multi-tenancy support, which assign no "
            "customers."
        ),
        example="Customer A",
    )
    folder: str | None = api_field(
        description=(
            "The Setup folder path the host is configured in, '/' for the root folder. Empty "
            "when the host isn't managed via Setup, e.g. it was added directly to the "
            "monitoring core."
        ),
        example="/network/switches",
    )
    contact_groups: list[str] = api_field(
        description="Contact groups assigned to the host",
        example=["all"],
    )
    tags: dict[str, str] = api_field(
        description="Host tags",
        example={"criticality": "prod"},
    )
    labels: dict[str, HostLabelValue] = api_field(
        description="Host labels",
        example={"cmk/os_family": HostLabelValue(value="linux", source="discovered")},
    )
    legacy_host_status_link: str = api_field(
        description="URL to legacy host status view",
        example="view.py?view_name=hoststatus&host=web-server-01&site=local",
    )

    @classmethod
    def from_domain(cls, host: Host, *, site_alias: str, customer: str | None) -> Self:
        def read[T](value: T | None, name: str) -> T:
            """The overview reads every column, so a missing one is a bug, not an omission."""
            if value is None:
                raise ValueError(f"host overview is missing {name!r}")
            return value

        return cls(
            name=host.name,
            state=host.state_label,
            address=read(host.address, "address"),
            alias=read(host.alias, "alias"),
            site_id=host.site_id,
            site_alias=site_alias,
            service_counts=read(host.service_counts, "service_counts"),
            modes=build_host_modes(host),
            last_check=read(host.last_check, "last_check"),
            last_state_change=read(host.last_state_change, "last_state_change"),
            customer=customer,
            folder=read(host.folder, "folder"),
            contact_groups=read(host.contact_groups, "contact_groups"),
            tags=read(host.tags, "tags"),
            labels=read(host.labels, "labels"),
            legacy_host_status_link=host_view_link("hoststatus", host),
        )


def get_host_overview(
    hostname: Annotated[
        AnnotatedHostName,
        PathParam(description="The host name", example="web-server-01"),
    ],
    site_id: Annotated[
        Annotated[SiteId, TypedPlainValidator(str, SiteIdConverter.should_exist)],
        QueryParam(description="An existing site id", example="local"),
    ],
    api_context: ApiContext,
) -> HostOverviewResponse:
    """Show the overview for a single host."""
    host_repo = LiveStatusHostRepository(connection=sites.live())
    site_alias = api_context.config.sites[site_id]["alias"]

    return _handle_get_host_overview(
        host_repo,
        hostname=hostname,
        site_id=site_id,
        site_alias=site_alias,
        customer=customer_resolver(sites=api_context.config.sites)(site_id),
    )


def _handle_get_host_overview(
    host_repo: HostRepository,
    *,
    hostname: str,
    site_id: str,
    site_alias: str,
    customer: str | None = None,
) -> HostOverviewResponse:
    try:
        host = host_repo.get_overview(hostname=hostname, site_id=site_id)
    except HostNotFoundError:
        raise ProblemException(
            status=404,
            title="The requested host was not found",
            detail=f"The host {hostname!r} was not found on site {site_id!r}",
        ) from None

    return HostOverviewResponse.from_domain(host, site_alias=site_alias, customer=customer)


ENDPOINT_GET_HOST_OVERVIEW = VersionedEndpoint(
    metadata=EndpointMetadata(
        path="/monitor/hosts/{hostname}",
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
    doc=EndpointDoc(family=MONITOR_HOSTS_FAMILY.name),
    behavior=EndpointBehavior(skip_locking=True),
    versions={APIVersion.INTERNAL: EndpointHandler(handler=get_host_overview)},
)
