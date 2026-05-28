#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Annotated, cast

from cmk.gui.logged_in import user
from cmk.gui.openapi.framework import (
    ApiContext,
    APIVersion,
    EndpointDoc,
    EndpointHandler,
    EndpointMetadata,
    EndpointPermissions,
    PathParam,
    VersionedEndpoint,
)
from cmk.gui.openapi.framework.model.constructors import generate_links
from cmk.gui.openapi.framework.model.converter import HostConverter, TypedPlainValidator
from cmk.gui.openapi.restful_objects.constructors import object_href
from cmk.gui.watolib.hosts_and_folders import Host

from ._family import SERVICE_DISCOVERY_FAMILY
from ._utils import job_snapshot, RO_PERMISSIONS
from .models.response_models import (
    ServiceDiscoveryRunExtensionsModel,
    ServiceDiscoveryRunLogsModel,
    ServiceDiscoveryRunModel,
    ServiceDiscoveryRunState,
)


def show_service_discovery_run_v1(
    api_context: ApiContext,
    host: Annotated[
        Annotated[Host, TypedPlainValidator(str, HostConverter().host)],
        PathParam(description="A host name.", example="example.com", alias="host_name"),
    ],
) -> ServiceDiscoveryRunModel:
    """Show the last service discovery background job on a host"""
    user.need_permission("wato.edit")
    user.need_permission("wato.services")
    user.need_permission("wato.see_all_folders")
    snapshot = job_snapshot(host, api_context.config.sites, debug=api_context.config.debug)
    job_id = snapshot.job_id
    job_status = snapshot.status
    return ServiceDiscoveryRunModel(
        domainType="service_discovery_run",
        id=job_id,
        title=f"Service discovery background job {job_id} is {job_status.state}",
        links=generate_links(
            domain_type="service_discovery_run",
            identifier=job_id,
            deletable=False,
            editable=False,
        ),
        extensions=ServiceDiscoveryRunExtensionsModel(
            active=job_status.is_active,
            state=cast(ServiceDiscoveryRunState, job_status.state),
            logs=ServiceDiscoveryRunLogsModel(
                result=list(job_status.loginfo["JobResult"]),
                progress=list(job_status.loginfo["JobProgressUpdate"]),
            ),
        ),
    )


ENDPOINT_SHOW_SERVICE_DISCOVERY_RUN = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=object_href("service_discovery_run", "{host_name}"),
        link_relation="cmk/show",
        method="get",
    ),
    permissions=EndpointPermissions(required=RO_PERMISSIONS),
    doc=EndpointDoc(family=SERVICE_DISCOVERY_FAMILY.name),
    versions={APIVersion.V1: EndpointHandler(handler=show_service_discovery_run_v1)},
)
