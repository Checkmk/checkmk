#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Annotated
from urllib.parse import urlparse

from cmk.gui.http import request
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
from cmk.gui.openapi.framework.model.converter import HostConverter, TypedPlainValidator
from cmk.gui.openapi.framework.model.response import ApiResponse
from cmk.gui.openapi.restful_objects.constructors import object_action_href
from cmk.gui.openapi.utils import ProblemException
from cmk.gui.watolib.hosts_and_folders import Host

from ._family import SERVICE_DISCOVERY_FAMILY
from ._utils import job_snapshot, RO_PERMISSIONS


def wait_for_service_discovery_completion_v1(
    api_context: ApiContext,
    host: Annotated[
        Annotated[Host, TypedPlainValidator(str, HostConverter().host)],
        PathParam(description="A host name.", example="example.com", alias="host_name"),
    ],
) -> ApiResponse[None]:
    """Wait for service discovery completion

    This endpoint will periodically redirect on itself to prevent timeouts.
    """
    user.need_permission("wato.edit")
    user.need_permission("wato.services")
    user.need_permission("wato.see_all_folders")

    snapshot = job_snapshot(host, api_context.config.sites, debug=api_context.config.debug)
    if not snapshot.exists:
        raise ProblemException(
            status=404,
            title="The requested service discovery job was not found",
            detail=f"Could not find a service discovery for host {host.name()}",
        )
    if snapshot.is_active:
        return ApiResponse(
            body=None,
            status_code=302,
            headers={"Location": urlparse(request.url).path},
        )
    return ApiResponse(body=None, status_code=204)


ENDPOINT_WAIT_FOR_SERVICE_DISCOVERY_COMPLETION = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=object_action_href("service_discovery_run", "{host_name}", "wait-for-completion"),
        link_relation="cmk/wait-for-completion",
        method="get",
        content_type=None,
    ),
    permissions=EndpointPermissions(required=RO_PERMISSIONS),
    doc=EndpointDoc(family=SERVICE_DISCOVERY_FAMILY.name),
    versions={
        APIVersion.V1: EndpointHandler(
            handler=wait_for_service_discovery_completion_v1,
            additional_status_codes=[302],
            status_descriptions={
                204: "The service discovery has been completed.",
                302: (
                    "The service discovery is still running. Redirecting to the "
                    "'Wait for completion' endpoint."
                ),
            },
        )
    },
)
