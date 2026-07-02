#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
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
from cmk.gui.openapi.restful_objects.constructors import collection_href
from cmk.gui.openapi.utils import ProblemException
from cmk.gui.watolib.hosts_and_folders import find_available_folder_name

from ._family import FOLDER_CONFIG_FAMILY
from ._utils import folder_etag, make_pending_changes, RW_PERMISSIONS, serialize_folder
from .models.request_models import CreateFolderModel


def create_folder_v1(api_context: ApiContext, body: CreateFolderModel) -> ApiResponse[FolderModel]:
    """Create a folder"""
    api_context.user.need_permission("wato.edit")
    parent_folder = body.parent
    name = body.name

    if name is not None and parent_folder.has_subfolder(name):
        raise ProblemException(
            status=400,
            title="The folder could not be created.",
            detail=f"A folder with name {name!r} already exists.",
        )

    if name is None:
        name = find_available_folder_name(body.title, parent_folder)

    folder = parent_folder.create_subfolder(
        name,
        body.title,
        body.attributes.to_internal(),
        pprint_value=api_context.config.wato_pprint_config,
        pending_changes=make_pending_changes(api_context),
        acting_user=api_context.user,
    )
    return ApiResponse(
        body=serialize_folder(folder, show_hosts=False, api_context=api_context),
        status_code=200,
        etag=folder_etag(folder),
    )


ENDPOINT_CREATE_FOLDER = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=collection_href("folder_config"),
        link_relation="cmk/create",
        method="post",
    ),
    permissions=EndpointPermissions(required=RW_PERMISSIONS),
    doc=EndpointDoc(family=FOLDER_CONFIG_FAMILY.name),
    versions={APIVersion.V1: EndpointHandler(handler=create_folder_v1)},
    behavior=EndpointBehavior(etag="output"),
)
