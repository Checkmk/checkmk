#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Annotated

from cmk.ccc.site import SiteId
from cmk.gui.logged_in import user
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
from cmk.gui.openapi.restful_objects.constructors import object_href
from cmk.gui.openapi.utils import ProblemException
from cmk.gui.quick_setup.handlers.stage import matching_stage_action, StageActionResult
from cmk.gui.quick_setup.handlers.utils import MKJobNotFoundException
from cmk.gui.quick_setup.v0_unstable._registry import quick_setup_registry
from cmk.gui.site_config import site_is_local
from cmk.gui.watolib.automations import (
    do_remote_automation,
    remote_automation_config_from_site_config,
)

from ._family import QUICK_SETUP_FAMILY
from ._utils import convert_stage_action_response, QUICK_SETUP_PERMISSIONS
from .models.response_models import QuickSetupStageActionResponseModel


def get_stage_action_result_v1(
    api_context: ApiContext,
    job_id: Annotated[
        str,
        PathParam(
            description="The id of the action job result to be fetched", example="quick_setup"
        ),
    ],
    site_id: Annotated[
        str | None,
        QueryParam(
            description="The site where the quick setup stage action result is located. Defaults to local site",
            example="foobar",
        ),
    ] = None,
) -> QuickSetupStageActionResponseModel:
    """Fetch the Quick setup stage action background job result"""
    if site_id and not site_is_local(site_config := api_context.config.sites[SiteId(site_id)]):
        action_result = StageActionResult.model_validate_json(
            str(
                do_remote_automation(
                    remote_automation_config_from_site_config(site_config),
                    "fetch-quick-setup-stage-action-result",
                    [("job_id", job_id)],
                    debug=api_context.config.debug,
                )
            )
        )
    else:
        try:
            action_result = StageActionResult.load_from_job_result(job_id=job_id)
        except MKJobNotFoundException:
            raise ProblemException(
                status=404,
                title="Job not found",
                detail=f"Background job '{job_id}' not found",
            )

    quick_setup = quick_setup_registry.get(action_result.quick_setup_id)
    if quick_setup is None:
        raise ProblemException(
            status=404,
            title="Quick setup not found",
            detail=f"Quick setup with id '{action_result.quick_setup_id}' does not exist.",
        )

    stage_action = matching_stage_action(
        quick_setup.stages[action_result.stage_index](), action_result.action_id
    )

    if stage_action.permissions is not None and not all(
        user.may(perm) for perm in stage_action.permissions
    ):
        raise ProblemException(
            status=403,
            title="Action not allowed",
            detail=(
                f"Action with id '{action_result.action_id}' requires "
                f"{', '.join(repr(x) for x in stage_action.permissions)} permissions."
            ),
        )

    return convert_stage_action_response(action_result)


ENDPOINT_GET_STAGE_ACTION_RESULT = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=object_href("quick_setup_stage_action_result", "{job_id}"),
        link_relation="cmk/show",
        method="get",
    ),
    permissions=EndpointPermissions(required=QUICK_SETUP_PERMISSIONS),
    doc=EndpointDoc(
        family=QUICK_SETUP_FAMILY.name,
    ),
    behavior=EndpointBehavior(skip_locking=True),
    versions={
        APIVersion.V1: EndpointHandler(
            handler=get_stage_action_result_v1, additional_status_codes=[403]
        )
    },
)
