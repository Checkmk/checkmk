#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Annotated

from cmk.gui.openapi.api_endpoints.models.folder_models import FolderModel
from cmk.gui.openapi.framework import (
    ApiContext,
    APIVersion,
    EndpointBehavior,
    EndpointDoc,
    EndpointHandler,
    EndpointMetadata,
    EndpointPermissions,
    QueryParam,
    VersionedEndpoint,
)
from cmk.gui.openapi.framework.model.response import ApiResponse
from cmk.gui.openapi.restful_objects.constructors import object_href

from ._family import FOLDER_CONFIG_FAMILY
from ._utils import folder_etag, FolderPathParam, READ_PERMISSIONS, serialize_folder


def show_folder_v1(
    api_context: ApiContext,
    folder: FolderPathParam,
    show_hosts: Annotated[
        bool,
        QueryParam(
            description=(
                "When set, all hosts that are stored in this folder will also be shown. On large "
                "setups this may come at a performance cost, so by default this is switched off."
            ),
            example="False",
        ),
    ] = False,
) -> ApiResponse[FolderModel]:
    """Show a folder"""
    folder.permissions.need_permission("read", api_context.user)
    return ApiResponse(
        body=serialize_folder(folder, show_hosts=show_hosts, api_context=api_context),
        status_code=200,
        etag=folder_etag(folder),
    )


ENDPOINT_SHOW_FOLDER = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=object_href("folder_config", "{folder}"),
        link_relation="cmk/show",
        method="get",
    ),
    permissions=EndpointPermissions(required=READ_PERMISSIONS),
    doc=EndpointDoc(family=FOLDER_CONFIG_FAMILY.name),
    versions={APIVersion.V1: EndpointHandler(handler=show_folder_v1)},
    behavior=EndpointBehavior(etag="output"),
)
