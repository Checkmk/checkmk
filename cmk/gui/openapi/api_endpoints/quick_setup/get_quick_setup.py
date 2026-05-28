#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Annotated, Literal

from cmk.gui import i18n
from cmk.gui.logged_in import user
from cmk.gui.openapi.framework import (
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
from cmk.gui.quick_setup.handlers.setup import (
    quick_setup_guided_mode,
    quick_setup_overview_mode,
)
from cmk.gui.quick_setup.v0_unstable._registry import quick_setup_registry
from cmk.gui.quick_setup.v0_unstable.setups import get_all_permissions
from cmk.gui.quick_setup.v0_unstable.type_defs import ParsedFormData

from ._family import QUICK_SETUP_FAMILY
from ._utils import convert_guided_response, convert_overview_response, QUICK_SETUP_PERMISSIONS
from .models.response_models import QuickSetupResponseModel


def get_quick_setup_v1(
    quick_setup_id: Annotated[str, PathParam(description="The quick setup id", example="aws")],
    mode: Annotated[
        Literal["guided", "overview"] | None,
        QueryParam(
            description="The quick setup mode",
            example="overview",
        ),
    ] = "guided",
    object_id: Annotated[
        str | None,
        QueryParam(
            description="Select object id to prefill data for the quick setup",
            example="8558f956-3e45-4c4f-bd02-e88da17c99dd",
        ),
    ] = None,
) -> QuickSetupResponseModel:
    """Get guided stages or overview stages"""
    i18n.localize(user.language)
    quick_setup = quick_setup_registry.get(quick_setup_id)
    if quick_setup is None:
        raise ProblemException(
            status=404,
            title="Quick setup not found",
            detail=f"Quick setup with id '{quick_setup_id}' does not exist.",
        )

    permissions = get_all_permissions(quick_setup)
    if permissions is not None and not all(user.may(perm) for perm in permissions):
        raise ProblemException(
            status=403,
            title="Action not allowed",
            detail=f"Requires {', '.join(repr(p) for p in permissions)} permissions.",
        )

    prefill_data: ParsedFormData | None = None
    if object_id:
        prefill_data = quick_setup.load_data(object_id)
        if not prefill_data:
            raise ProblemException(
                status=404,
                title="Object not found",
                detail=f"Object with id '{object_id}' does not exist.",
            )

    if mode == "overview":
        return convert_overview_response(
            quick_setup_overview_mode(
                quick_setup=quick_setup,
                prefill_data=prefill_data,
                is_edit_mode=bool(object_id),
            )
        )
    return convert_guided_response(
        quick_setup_guided_mode(
            quick_setup=quick_setup,
            prefill_data=prefill_data,
            is_edit_mode=bool(object_id),
        )
    )


ENDPOINT_GET_QUICK_SETUP = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=object_href("quick_setup", "{quick_setup_id}"),
        link_relation="cmk/quick_setup",
        method="get",
    ),
    permissions=EndpointPermissions(required=QUICK_SETUP_PERMISSIONS),
    doc=EndpointDoc(
        family=QUICK_SETUP_FAMILY.name,
    ),
    behavior=EndpointBehavior(skip_locking=True),
    versions={
        APIVersion.V1: EndpointHandler(handler=get_quick_setup_v1, additional_status_codes=[403])
    },
)
