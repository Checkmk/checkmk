#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Sequence
from typing import Annotated

from cmk.ccc.hostaddress import HostName
from cmk.ccc.site import SiteId
from cmk.gui.background_job.job import InitialStatusArgs, JobTarget
from cmk.gui.openapi.framework import (
    ApiContext,
    APIVersion,
    EndpointBehavior,
    EndpointDoc,
    EndpointHandler,
    EndpointMetadata,
    EndpointPermissions,
    PathParam,
    VersionedEndpoint,
)
from cmk.gui.openapi.framework.endpoint_link import path_to_endpoint
from cmk.gui.openapi.framework.model import api_field, api_model
from cmk.gui.openapi.framework.model.converter import HostConverter, TypedPlainValidator
from cmk.gui.openapi.framework.model.response import ApiResponse
from cmk.gui.openapi.restful_objects.constructors import object_action_href
from cmk.gui.openapi.utils import ProblemException
from cmk.gui.watolib.activate_changes import ActivateChanges
from cmk.gui.watolib.configuration_bundle_store import is_locked_by_quick_setup
from cmk.gui.watolib.host_rename import (
    rename_hosts_job_entry_point,
    RenameHostBackgroundJob,
    RenameHostsJobArgs,
)
from cmk.gui.watolib.hosts_and_folders import Host
from cmk.web.utils import permission_verification as permissions

from ._family import HOST_CONFIG_FAMILY
from ._utils import host_etag

PERMISSIONS_RENAME = permissions.AllPerm(
    [
        permissions.Perm("wato.all_folders"),
        permissions.Perm("wato.edit_hosts"),
        permissions.Perm("wato.rename_hosts"),
        permissions.Perm("wato.see_all_folders"),
    ]
)


def _has_pending_changes(sites: Sequence[SiteId]) -> bool:
    return ActivateChanges.get_pending_changes_info(sites).has_changes()


@api_model
class RenameHostModel:
    new_name: Annotated[HostName, TypedPlainValidator(str, HostConverter.not_exists)] = api_field(
        description="The new name of the existing host.",
        example="newhost",
    )


def rename_host_v1(
    api_context: ApiContext,
    body: RenameHostModel,
    host: Annotated[
        Annotated[
            Host,
            TypedPlainValidator(str, HostConverter(permission_type="setup_write").host),
        ],
        PathParam(description="Host name", example="example.com", alias="host_name"),
    ],
) -> ApiResponse[None]:
    """Rename a host

    This endpoint will start a background job to rename the host. Only one rename background job
    can run at a time.
    """
    api_context.user.need_permission("wato.edit_hosts")
    api_context.user.need_permission("wato.rename_hosts")
    if _has_pending_changes(list(api_context.config.sites)):
        raise ProblemException(
            status=409,
            title="Pending changes are present",
            detail="Please activate all pending changes before executing a host rename process",
        )

    new_name = body.new_name
    if is_locked_by_quick_setup(host.locked_by()):
        raise ProblemException(
            status=400,
            title=f'The host "{host.name()}" is locked by Quick setup.',
            detail="Locked hosts cannot be renamed.",
        )

    background_job = RenameHostBackgroundJob(host)
    result = background_job.start(
        JobTarget(
            callable=rename_hosts_job_entry_point,
            args=RenameHostsJobArgs(
                renamings=[(host.folder().path(), host.name(), new_name)],
                site_configs=api_context.config.sites,
                pprint_value=api_context.config.wato_pprint_config,
                use_git=api_context.config.wato_use_git,
                debug=api_context.config.debug,
                custom_user_attributes=api_context.config.wato_user_attrs,
                user_connections=api_context.config.user_connections,
                user_permission_config=api_context.config.user_permissions().to_serializable_config(),
            ),
        ),
        InitialStatusArgs(
            title=f"Renaming of {host.name()} -> {new_name}",
            lock_wato=True,
            stoppable=False,
            estimated_duration=background_job.get_status().duration,
            user=str(api_context.user.id) if api_context.user.id else None,
        ),
    )
    if result.is_error():
        raise ProblemException(status=409, title="Conflict", detail=str(result.error))

    return ApiResponse(
        body=None,
        status_code=303,
        headers={
            "Location": path_to_endpoint(
                family=HOST_CONFIG_FAMILY.name,
                link_relation="cmk/wait-for-completion",
                version=api_context.version,
                parameters={},
            )
        },
        etag=host_etag(host),
    )


ENDPOINT_RENAME_HOST = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=object_action_href("host_config", "{host_name}", action_name="rename"),
        link_relation="cmk/rename",
        method="put",
        content_type=None,
    ),
    permissions=EndpointPermissions(required=PERMISSIONS_RENAME),
    doc=EndpointDoc(family=HOST_CONFIG_FAMILY.name),
    versions={
        APIVersion.V1: EndpointHandler(
            handler=rename_host_v1,
            additional_status_codes=[303, 409, 422],
            status_descriptions={
                303: (
                    "The host rename process is still running. Redirecting to the "
                    "'Wait for completion' endpoint"
                ),
                409: (
                    "There are pending changes not yet activated or a rename background job is "
                    "already running."
                ),
                422: "The host could not be renamed.",
            },
        )
    },
    behavior=EndpointBehavior(etag="both"),
)
