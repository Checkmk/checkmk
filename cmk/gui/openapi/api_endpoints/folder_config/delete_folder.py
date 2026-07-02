#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Annotated, Literal

from cmk.gui.openapi.framework import (
    ApiContext,
    APIVersion,
    EndpointDoc,
    EndpointHandler,
    EndpointMetadata,
    EndpointPermissions,
    QueryParam,
    VersionedEndpoint,
)
from cmk.gui.openapi.framework.model.response import ApiResponse
from cmk.gui.openapi.restful_objects.constructors import object_href
from cmk.gui.openapi.utils import ProblemException

from ._family import FOLDER_CONFIG_FAMILY
from ._utils import FolderPathParam, make_pending_changes, RW_PERMISSIONS


def delete_folder_v1(
    api_context: ApiContext,
    folder: FolderPathParam,
    delete_mode: Annotated[
        Literal["recursive", "abort_on_nonempty"],
        QueryParam(
            description=(
                "Delete policy: 'recursive': Deletes the folder and all the elements it contains. "
                "'abort_on_nonempty': Deletes the folder only if it is not empty."
            ),
            example="abort_on_nonempty",
        ),
    ] = "recursive",
) -> ApiResponse[None]:
    """Delete a folder"""
    api_context.user.need_permission("wato.edit")

    parent = folder.parent()
    if parent is None:
        raise ProblemException(
            status=401,
            title="Problem deleting folder.",
            detail="Deleting the root folder is not permitted.",
        )

    if delete_mode != "recursive" and (not folder.is_empty() or folder.is_referenced()):
        raise ProblemException(
            status=409,
            title="Problem deleting folder.",
            detail=(
                "Folder is not empty or is referenced by another object. Use the force parameter "
                "to delete it."
            ),
        )

    parent.delete_subfolder(
        folder.name(),
        pending_changes=make_pending_changes(api_context),
        acting_user=api_context.user,
    )
    return ApiResponse(body=None, status_code=204)


ENDPOINT_DELETE_FOLDER = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=object_href("folder_config", "{folder}"),
        link_relation=".../delete",
        method="delete",
        content_type=None,
    ),
    permissions=EndpointPermissions(required=RW_PERMISSIONS),
    doc=EndpointDoc(family=FOLDER_CONFIG_FAMILY.name),
    versions={
        APIVersion.V1: EndpointHandler(
            handler=delete_folder_v1,
            additional_status_codes=[401, 409],
        )
    },
)
