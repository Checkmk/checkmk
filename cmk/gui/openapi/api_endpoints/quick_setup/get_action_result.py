#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Annotated

from cmk.gui.logged_in import user
from cmk.gui.openapi.framework import (
    APIVersion,
    EndpointBehavior,
    EndpointDoc,
    EndpointHandler,
    EndpointMetadata,
    EndpointPermissions,
    PathParam,
    VersionedEndpoint,
)
from cmk.gui.openapi.restful_objects.constructors import object_href
from cmk.gui.openapi.utils import ProblemException
from cmk.gui.quick_setup.handlers.setup import CompleteActionResult
from cmk.gui.quick_setup.handlers.utils import MKJobNotFoundException
from cmk.gui.quick_setup.v0_unstable._registry import quick_setup_registry
from cmk.gui.quick_setup.v0_unstable.setups import get_all_permissions

from ._family import QUICK_SETUP_FAMILY
from ._utils import convert_complete_response, QUICK_SETUP_PERMISSIONS
from .models.response_models import QuickSetupCompleteResponseModel


def get_action_result_v1(
    job_id: Annotated[
        str,
        PathParam(
            description="The id of the action job result to be fetched", example="quick_setup"
        ),
    ],
) -> QuickSetupCompleteResponseModel:
    """Fetch the Quick action background job result"""
    try:
        action_result = CompleteActionResult.load_from_job_result(job_id=job_id)
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

    permissions = get_all_permissions(quick_setup)
    if permissions is not None and not all(user.may(perm) for perm in permissions):
        raise ProblemException(
            status=403,
            title="Action not allowed",
            detail=f"Requires {', '.join(repr(p) for p in permissions)} permissions.",
        )

    return convert_complete_response(action_result)


ENDPOINT_GET_ACTION_RESULT = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=object_href("quick_setup_action_result", "{job_id}"),
        link_relation=".../fetch",
        method="get",
    ),
    permissions=EndpointPermissions(required=QUICK_SETUP_PERMISSIONS),
    doc=EndpointDoc(
        family=QUICK_SETUP_FAMILY.name,
    ),
    behavior=EndpointBehavior(skip_locking=True),
    versions={
        APIVersion.V1: EndpointHandler(handler=get_action_result_v1, additional_status_codes=[403])
    },
)
