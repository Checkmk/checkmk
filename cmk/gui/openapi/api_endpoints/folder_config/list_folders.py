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
    QueryParam,
    VersionedEndpoint,
)
from cmk.gui.openapi.framework.model.common_fields import AnnotatedFolder
from cmk.gui.openapi.restful_objects.constructors import collection_href
from cmk.gui.watolib.hosts_and_folders import make_folder_tree

from ._family import FOLDER_CONFIG_FAMILY
from ._utils import READ_PERMISSIONS, serialize_folders_collection
from .models.response_models import FolderCollectionModel


def list_folders_v1(
    api_context: ApiContext,
    parent: Annotated[
        AnnotatedFolder | None,
        QueryParam(
            description="Show all sub-folders of this folder. The default is the root-folder.",
            example="/servers",
        ),
    ] = None,
    recursive: Annotated[
        bool,
        QueryParam(
            description="List the folder (default: root) and all its sub-folders recursively.",
            example="False",
        ),
    ] = False,
    show_hosts: Annotated[
        bool,
        QueryParam(
            description=(
                "When set, all hosts that are stored in each folder will also be shown. On large "
                "setups this may come at a performance cost, so by default this is switched off."
            ),
            example="False",
        ),
    ] = False,
) -> FolderCollectionModel:
    """Show all folders"""
    parent_folder = make_folder_tree(api_context.config).root_folder() if parent is None else parent
    if recursive:
        parent_folder.need_recursive_permission("read", api_context.user)
        folders = parent_folder.subfolders_recursively()
    else:
        parent_folder.permissions.need_permission("read", api_context.user)
        folders = parent_folder.subfolders()
    return serialize_folders_collection(folders, show_hosts=show_hosts, api_context=api_context)


ENDPOINT_LIST_FOLDERS = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=collection_href("folder_config"),
        link_relation=".../collection",
        method="get",
    ),
    permissions=EndpointPermissions(required=READ_PERMISSIONS),
    doc=EndpointDoc(family=FOLDER_CONFIG_FAMILY.name),
    versions={APIVersion.V1: EndpointHandler(handler=list_folders_v1)},
)
