#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Annotated

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
from cmk.gui.openapi.restful_objects.constructors import sub_object_href
from cmk.gui.openapi.utils import ProblemException
from cmk.gui.quick_setup.handlers.stage import get_stage_structure
from cmk.gui.quick_setup.v0_unstable._registry import quick_setup_registry
from cmk.gui.quick_setup.v0_unstable.setups import get_all_permissions
from cmk.gui.quick_setup.v0_unstable.type_defs import ParsedFormData

from ._family import QUICK_SETUP_FAMILY
from ._utils import _convert_stage_structure, QUICK_SETUP_PERMISSIONS
from .models.response_models import StageStructureModel


def get_stage_structure_v1(
    quick_setup_id: Annotated[str, PathParam(description="The quick setup id", example="aws")],
    stage_index: Annotated[str, PathParam(description="The stage index", example="1")],
    object_id: Annotated[
        str | None,
        QueryParam(
            description="Select object id to prefill data for the quick setup",
            example="8558f956-3e45-4c4f-bd02-e88da17c99dd",
        ),
    ] = None,
) -> StageStructureModel:
    """Get a Quick setup stage structure"""
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

    stage_idx = int(stage_index)
    return _convert_stage_structure(
        get_stage_structure(
            stage=quick_setup.stages[stage_idx](),
            prefill_data=prefill_data,
        )
    )


ENDPOINT_GET_STAGE_STRUCTURE = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=sub_object_href(
            domain_type="quick_setup_stage",
            obj_id="{stage_index}",
            parent_domain_type="quick_setup",
            parent_id="{quick_setup_id}",
        ),
        link_relation="cmk/fetch",
        method="get",
    ),
    permissions=EndpointPermissions(required=QUICK_SETUP_PERMISSIONS),
    doc=EndpointDoc(
        family=QUICK_SETUP_FAMILY.name,
    ),
    behavior=EndpointBehavior(skip_locking=True),
    versions={
        APIVersion.V1: EndpointHandler(
            handler=get_stage_structure_v1, additional_status_codes=[403]
        )
    },
)
