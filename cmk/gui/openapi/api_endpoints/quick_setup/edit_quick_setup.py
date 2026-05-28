#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Annotated

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
from cmk.gui.openapi.framework.model.response import ApiResponse
from cmk.gui.openapi.restful_objects.constructors import object_action_href
from cmk.gui.quick_setup.v0_unstable.setups import QuickSetupActionMode

from ._family import QUICK_SETUP_FAMILY
from ._utils import complete_quick_setup_action, QUICK_SETUP_PERMISSIONS
from .models.request_models import QuickSetupFinalActionRequestModel
from .models.response_models import QuickSetupCompleteResponseModel


def edit_quick_setup_v1(
    api_context: ApiContext,
    quick_setup_id: Annotated[str, PathParam(description="The quick setup id", example="aws")],
    body: QuickSetupFinalActionRequestModel,
    object_id: Annotated[
        str,
        QueryParam(
            description="Select object id to prefill data for the quick setup",
            example="8558f956-3e45-4c4f-bd02-e88da17c99dd",
        ),
    ],
    search: Annotated[
        str | None,
        QueryParam(
            description="Optional search query to preserve when redirecting after save",
            example="my rule",
        ),
    ] = None,
) -> ApiResponse[QuickSetupCompleteResponseModel]:
    """Edit the quick setup"""
    return complete_quick_setup_action(
        api_context=api_context,
        quick_setup_id=quick_setup_id,
        body=body,
        mode=QuickSetupActionMode.EDIT,
        object_id=object_id,
    )


ENDPOINT_EDIT_QUICK_SETUP = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=object_action_href("quick_setup", "{quick_setup_id}", "edit"),
        link_relation="cmk/edit_quick_setup",
        method="put",
    ),
    permissions=EndpointPermissions(required=QUICK_SETUP_PERMISSIONS),
    doc=EndpointDoc(
        family=QUICK_SETUP_FAMILY.name,
    ),
    versions={
        APIVersion.V1: EndpointHandler(
            handler=edit_quick_setup_v1,
            additional_status_codes=[201, 303, 403, 429],
        )
    },
)
