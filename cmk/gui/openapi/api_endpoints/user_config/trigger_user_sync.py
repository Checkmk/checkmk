#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.background_job.job import InitialStatusArgs, JobTarget
from cmk.gui.logged_in import user
from cmk.gui.openapi.api_endpoints.background_job import BACKGROUND_JOB_FAMILY
from cmk.gui.openapi.framework import (
    ApiContext,
    APIVersion,
    EndpointDoc,
    EndpointHandler,
    EndpointMetadata,
    EndpointPermissions,
    VersionedEndpoint,
)
from cmk.gui.openapi.framework.endpoint_link import path_to_endpoint
from cmk.gui.openapi.framework.model.response import ApiResponse
from cmk.gui.openapi.restful_objects.constructors import domain_type_action_href
from cmk.gui.openapi.shared_endpoint_families.user_config import USER_CONFIG_FAMILY
from cmk.gui.openapi.utils import ProblemException
from cmk.gui.userdb.user_sync_job import sync_entry_point, UserSyncArgs, UserSyncBackgroundJob
from cmk.gui.utils import permission_verification as permissions


def trigger_user_sync_v1(api_context: ApiContext) -> ApiResponse[None]:
    """Synchronize users

    Starts the user synchronization background job, which synchronizes the users of all
    active user connections (for example LDAP). This is the same job that is triggered by
    the "Synchronize users" button in the user interface and by the regular synchronization
    interval.
    """
    user.need_permission("wato.users")

    job = UserSyncBackgroundJob()
    if (
        result := job.start(
            JobTarget(
                callable=sync_entry_point,
                args=UserSyncArgs(
                    add_to_changelog=False,
                    enforce_sync=True,
                    custom_user_attributes=api_context.config.wato_user_attrs,
                    default_user_profile=api_context.config.default_user_profile,
                    user_permission_config=api_context.config.user_permissions().to_serializable_config(),
                ),
            ),
            InitialStatusArgs(
                title=job.gui_title(),
                stoppable=False,
                user=str(user.id) if user.id else None,
            ),
        )
    ).is_error():
        raise ProblemException(409, f"Could not start the user synchronization: {result.error}")

    return ApiResponse(
        body=None,
        status_code=303,
        headers={
            "Location": path_to_endpoint(
                family=BACKGROUND_JOB_FAMILY.name,
                link_relation="cmk/show",
                version=api_context.version,
                parameters={"job_id": job.get_job_id()},
            )
        },
    )


ENDPOINT_TRIGGER_USER_SYNC = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=domain_type_action_href("user_config", "sync"),
        link_relation="cmk/activate",
        method="post",
        content_type=None,
    ),
    permissions=EndpointPermissions(required=permissions.Perm("wato.users")),
    doc=EndpointDoc(family=USER_CONFIG_FAMILY.name),
    versions={
        APIVersion.UNSTABLE: EndpointHandler(
            handler=trigger_user_sync_v1,
            additional_status_codes=[303, 409],
            status_descriptions={
                303: (
                    "The user synchronization job has been started in the background. "
                    "Redirecting to the 'Get background job status snapshot' endpoint."
                ),
                409: "A user synchronization job is already running.",
            },
        )
    },
)
