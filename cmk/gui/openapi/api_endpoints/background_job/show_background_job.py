#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from typing import Annotated

from cmk.ccc.site import omd_site, SiteId
from cmk.gui.background_job.job import BackgroundJob, BackgroundStatusSnapshot
from cmk.gui.logged_in import user
from cmk.gui.openapi.framework import (
    ApiContext,
    APIVersion,
    EndpointDoc,
    EndpointHandler,
    EndpointMetadata,
    EndpointPermissions,
    PathParam,
    QueryParam,
    VersionedEndpoint,
)
from cmk.gui.openapi.framework.model.constructors import generate_links
from cmk.gui.openapi.restful_objects.constructors import object_href
from cmk.gui.openapi.utils import ProblemException
from cmk.gui.site_config import site_is_local
from cmk.gui.utils import permission_verification as permissions
from cmk.gui.watolib.automations import (
    do_remote_automation,
    remote_automation_config_from_site_config,
)

from ._family import BACKGROUND_JOB_FAMILY
from .models.response_models import (
    BackgroundJobSnapshotExtensionsModel,
    BackgroundJobSnapshotObjectModel,
    BackgroundJobStatusModel,
    StatusLogInfoModel,
)

PERMISSIONS = permissions.AllPerm(
    [
        permissions.Perm("background_jobs.manage_jobs"),
        permissions.Optional(permissions.Perm("background_jobs.delete_jobs")),
        permissions.Optional(permissions.Perm("background_jobs.stop_jobs")),
        permissions.Optional(permissions.Perm("background_jobs.stop_foreign_jobs")),
    ]
)


def show_background_job_v1(
    api_context: ApiContext,
    job_id: Annotated[
        str,
        PathParam(
            description="The ID of the background job",
            example="foobar",
        ),
    ],
    site_id: Annotated[
        str | None,
        QueryParam(
            description="The site where the background job is located. Defaults to local site",
            example="foobar",
        ),
    ] = None,
) -> BackgroundJobSnapshotObjectModel:
    """Show the last status of a background job"""
    user.need_permission("background_jobs.manage_jobs")

    resolved_site_id = SiteId(site_id) if site_id is not None else omd_site()

    if resolved_site_id not in api_context.config.sites:
        raise ProblemException(
            status=400,
            title="Unknown site",
            detail=f"No site with the ID '{resolved_site_id}' is configured",
        )
    site_config = api_context.config.sites[resolved_site_id]
    if not site_is_local(site_config):
        snapshot = BackgroundStatusSnapshot.from_dict(
            json.loads(
                str(
                    do_remote_automation(
                        remote_automation_config_from_site_config(site_config),
                        command="fetch-background-job-snapshot",
                        vars_=[("job_id", job_id)],
                        debug=api_context.config.debug,
                    )
                )
            )
        )
    else:
        background_job = BackgroundJob(job_id)
        snapshot = background_job.get_status_snapshot()

    if not snapshot.exists:
        raise ProblemException(
            status=404,
            title="The requested background job does not exist",
            detail=f"Could not find a background job with the ID '{job_id}' on site {resolved_site_id}",
        )

    status = snapshot.status
    return BackgroundJobSnapshotObjectModel(
        domainType="background_job",
        id=job_id,
        title=f"Background job {job_id} {'is active' if snapshot.is_active else 'is finished'}",
        extensions=BackgroundJobSnapshotExtensionsModel(
            site_id=str(resolved_site_id),
            active=snapshot.is_active,
            status=BackgroundJobStatusModel(
                state=status.state,
                log_info=StatusLogInfoModel(
                    JobProgressUpdate=list(status.loginfo["JobProgressUpdate"]),
                    JobResult=list(status.loginfo["JobResult"]),
                    JobException=list(status.loginfo["JobException"]),
                ),
            ),
        ),
        links=generate_links(
            domain_type="background_job",
            identifier=job_id,
            deletable=False,
            editable=False,
        ),
    )


ENDPOINT_SHOW_BACKGROUND_JOB = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=object_href("background_job", "{job_id}"),
        link_relation="cmk/show",
        method="get",
    ),
    permissions=EndpointPermissions(required=PERMISSIONS),
    doc=EndpointDoc(family=BACKGROUND_JOB_FAMILY.name),
    versions={APIVersion.V1: EndpointHandler(handler=show_background_job_v1)},
)
