#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from enum import StrEnum
from typing import Annotated, Literal

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


class QuickSetupMode(StrEnum):
    GUIDED = "guided"
    OVERVIEW = "overview"


def run_quick_setup_action_v1(
    api_context: ApiContext,
    quick_setup_id: Annotated[str, PathParam(description="The quick setup id", example="aws")],
    body: QuickSetupFinalActionRequestModel,
    mode: Annotated[
        Literal["guided", "overview"] | None,
        QueryParam(description="The quick setup mode", example="overview"),
    ] = "guided",
    search: Annotated[
        str | None,
        QueryParam(
            description="Optional search query to preserve when redirecting after save",
            example="my rule",
        ),
    ] = None,
) -> ApiResponse[QuickSetupCompleteResponseModel]:
    """Run a quick setup action"""
    return complete_quick_setup_action(
        api_context=api_context,
        quick_setup_id=quick_setup_id,
        body=body,
        mode=QuickSetupActionMode.SAVE,
    )


ENDPOINT_RUN_QUICK_SETUP_ACTION = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=object_action_href("quick_setup", "{quick_setup_id}", "run-action"),
        link_relation="cmk/run_setup",
        method="post",
    ),
    permissions=EndpointPermissions(required=QUICK_SETUP_PERMISSIONS),
    doc=EndpointDoc(
        family=QUICK_SETUP_FAMILY.name,
    ),
    versions={
        APIVersion.V1: EndpointHandler(
            handler=run_quick_setup_action_v1,
            additional_status_codes=[201, 303, 403, 429],
        )
    },
)
