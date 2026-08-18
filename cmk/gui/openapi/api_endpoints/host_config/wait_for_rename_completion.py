#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from urllib.parse import urlparse

from cmk.gui.http import request
from cmk.gui.openapi.framework import (
    ApiContext,
    APIVersion,
    EndpointDoc,
    EndpointHandler,
    EndpointMetadata,
    EndpointPermissions,
    VersionedEndpoint,
)
from cmk.gui.openapi.framework.model.response import ApiResponse
from cmk.gui.openapi.restful_objects.constructors import domain_type_action_href
from cmk.gui.openapi.utils import ProblemException
from cmk.gui.watolib.host_rename import RenameHostsBackgroundJob
from cmk.web.utils import permission_verification as permissions

from ._family import HOST_CONFIG_FAMILY

PERMISSIONS_WAIT = permissions.AllPerm([permissions.Perm("wato.rename_hosts")])


def wait_for_rename_completion_v1(api_context: ApiContext) -> ApiResponse[None]:
    """Wait for renaming process completion

    This endpoint will redirect on itself to prevent timeouts.
    """
    api_context.user.need_permission("wato.rename_hosts")

    job_exists, job_is_active = RenameHostsBackgroundJob.status_checks()
    if not job_exists:
        raise ProblemException(
            status=404,
            title="Not found",
            detail="No running renaming job was found",
        )

    if job_is_active:
        return ApiResponse(
            body=None,
            status_code=302,
            headers={"Location": urlparse(request.url).path},
        )
    return ApiResponse(body=None, status_code=204)


ENDPOINT_WAIT_FOR_RENAME_COMPLETION = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=domain_type_action_href("host_config", "wait-for-completion"),
        link_relation="cmk/wait-for-completion",
        method="get",
        content_type=None,
    ),
    permissions=EndpointPermissions(required=PERMISSIONS_WAIT),
    doc=EndpointDoc(family=HOST_CONFIG_FAMILY.name),
    versions={
        APIVersion.V1: EndpointHandler(
            handler=wait_for_rename_completion_v1,
            additional_status_codes=[302, 404],
            status_descriptions={
                204: "The renaming job has been completed.",
                302: (
                    "The renaming job is still running. Redirecting to the 'Wait for completion' "
                    "endpoint."
                ),
                404: "There is no running renaming job",
            },
        )
    },
)
