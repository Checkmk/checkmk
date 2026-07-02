#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.gui.exceptions import MKUserError
from cmk.gui.openapi.api_endpoints.models.folder_models import FolderModel
from cmk.gui.openapi.framework import (
    ApiContext,
    APIVersion,
    EndpointBehavior,
    EndpointDoc,
    EndpointHandler,
    EndpointMetadata,
    EndpointPermissions,
    VersionedEndpoint,
)
from cmk.gui.openapi.framework.model.response import ApiResponse
from cmk.gui.openapi.restful_objects.constructors import object_action_href
from cmk.gui.openapi.utils import ProblemException
from cmk.gui.watolib.hosts_and_folders import folder_tree

from ._family import FOLDER_CONFIG_FAMILY
from ._utils import (
    folder_etag,
    FolderPathParam,
    make_pending_changes,
    RW_PERMISSIONS,
    serialize_folder,
)
from .models.request_models import MoveFolderModel


def move_folder_v1(
    api_context: ApiContext,
    body: MoveFolderModel,
    folder: FolderPathParam,
) -> ApiResponse[FolderModel]:
    """Move a folder"""
    api_context.user.need_permission("wato.edit")
    folder_id = folder.id()
    if api_context.etag.enabled:
        api_context.etag.verify(folder_etag(folder))

    if folder.is_root():
        raise ProblemException(
            status=400,
            title="Problem moving folder",
            detail="You can't move the root folder.",
        )

    try:
        parent = folder.parent()
        assert parent is not None
        parent.move_subfolder_to(
            folder,
            body.destination,
            pprint_value=api_context.config.wato_pprint_config,
            pending_changes=make_pending_changes(api_context),
            acting_user=api_context.user,
        )
    except MKUserError as exc:
        raise ProblemException(
            status=400,
            title="Problem moving folder.",
            detail=exc.message,
        )

    moved_folder = folder_tree()._by_id(folder_id)
    return ApiResponse(
        body=serialize_folder(moved_folder, show_hosts=False, api_context=api_context),
        status_code=200,
        etag=folder_etag(moved_folder),
    )


ENDPOINT_MOVE_FOLDER = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=object_action_href("folder_config", "{folder}", action_name="move"),
        link_relation="cmk/move",
        method="post",
    ),
    permissions=EndpointPermissions(required=RW_PERMISSIONS),
    doc=EndpointDoc(family=FOLDER_CONFIG_FAMILY.name),
    versions={APIVersion.V1: EndpointHandler(handler=move_folder_v1)},
    behavior=EndpointBehavior(etag="both"),
)
