#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Background Jobs

A background job allows certain tasks to be run as background processes. It should be kept in
mind that some jobs lock certain areas in the Setup to prevent further configurations as long
as the background process is running.

"""

import json
from collections.abc import Mapping
from typing import Any

from cmk.ccc.site import omd_site, SiteId

from cmk.gui.background_job import BackgroundJob, BackgroundStatusSnapshot
from cmk.gui.config import active_config
from cmk.gui.http import Response
from cmk.gui.openapi.endpoints.background_job.response_schemas import BackgroundJobSnapshotObject
from cmk.gui.openapi.restful_objects import constructors, Endpoint
from cmk.gui.openapi.restful_objects.registry import EndpointRegistry
from cmk.gui.openapi.utils import problem, serve_json
from cmk.gui.site_config import site_is_local
from cmk.gui.watolib.automations import do_remote_automation, RemoteAutomationConfig

from cmk import fields as gui_fields


class JobID:
    field_name = "job_id"
    field_definition = gui_fields.String(
        description="The ID of the background job",
        example="foobar",
        required=True,
    )


class FieldSiteId:
    field_name = "site_id"
    field_definition = gui_fields.String(
        description="The site where the background job is located. Defaults to local site",
        example="foobar",
        required=False,
    )


@Endpoint(
    constructors.object_href(domain_type="background_job", obj_id=f"{{{JobID.field_name}}}"),
    # We leave the endpoint internal for now as a lot of individual domains have their own
    # implementation of background jobs and we should migrate them at some point.
    tag_group="Checkmk Internal",
    link_relation="cmk/show",
    method="get",
    path_params=[
        {
            JobID.field_name: JobID.field_definition,
        }
    ],
    query_params=[
        {
            FieldSiteId.field_name: FieldSiteId.field_definition,
        }
    ],
    response_schema=BackgroundJobSnapshotObject,
)
def show_background_job_snapshot(params: Mapping[str, Any]) -> Response:
    """Show the last status of a background job"""
    job_id = params[JobID.field_name]
    if (site_id_value := params.get(FieldSiteId.field_name)) is not None:
        site_id = SiteId(site_id_value)
    else:
        site_id = omd_site()

    if not site_is_local(site_config := active_config.sites[site_id]):
        snapshot = BackgroundStatusSnapshot.from_dict(
            json.loads(
                str(
                    do_remote_automation(
                        RemoteAutomationConfig.from_site_config(site_config),
                        command="fetch-background-job-snapshot",
                        vars_=[("job_id", job_id)],
                        debug=active_config.debug,
                    )
                )
            )
        )
    else:
        background_job = BackgroundJob(job_id)
        snapshot = background_job.get_status_snapshot()

    if not snapshot.exists:
        return problem(
            status=404,
            title="The requested background job does not exist",
            detail=f"Could not find a background job with the ID '{job_id}' on site {site_id}",
        )

    status = snapshot.status
    return serve_json(
        constructors.domain_object(
            domain_type="background_job",
            identifier=job_id,
            title=f"Background job {job_id} {'is active' if snapshot.is_active else 'is finished'}",
            extensions={
                "site_id": site_id,
                # TODO: add the snapshot fields
                "active": snapshot.is_active,
                "status": {"state": status.state, "log_info": status.loginfo},
            },
            deletable=False,
            editable=False,
        )
    )


def register(endpoint_registry: EndpointRegistry, *, ignore_duplicates: bool) -> None:
    endpoint_registry.register(show_background_job_snapshot, ignore_duplicates=ignore_duplicates)
