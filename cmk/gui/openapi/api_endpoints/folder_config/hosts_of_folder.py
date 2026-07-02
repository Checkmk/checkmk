#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Annotated

from cmk.gui.openapi.api_endpoints.host_config._utils import serialize_host_collection
from cmk.gui.openapi.api_endpoints.host_config.models.response_models import (
    HostConfigCollectionModel,
)
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
from cmk.gui.openapi.restful_objects.constructors import domain_object_collection_href

from ._family import FOLDER_CONFIG_FAMILY
from ._utils import FolderPathParam, READ_PERMISSIONS


def hosts_of_folder_v1(
    api_context: ApiContext,
    folder: FolderPathParam,
    effective_attributes: Annotated[
        bool,
        QueryParam(
            description=(
                "Show all effective attributes on hosts, not just the attributes which were set on "
                "this host specifically. This includes all attributes of all of this host's parent "
                "folders."
            ),
            example="False",
        ),
    ] = False,
) -> HostConfigCollectionModel:
    """Show all hosts in a folder"""
    folder.permissions.need_permission("read", api_context.user)
    return serialize_host_collection(
        folder.hosts().values(),
        api_context=api_context,
        compute_effective_attributes=effective_attributes,
        compute_links=False,
    )


ENDPOINT_HOSTS_OF_FOLDER = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=domain_object_collection_href("folder_config", "{folder}", "hosts"),
        link_relation="cmk/list",
        method="get",
    ),
    permissions=EndpointPermissions(required=READ_PERMISSIONS),
    doc=EndpointDoc(family=FOLDER_CONFIG_FAMILY.name),
    versions={APIVersion.V1: EndpointHandler(handler=hosts_of_folder_v1)},
)
