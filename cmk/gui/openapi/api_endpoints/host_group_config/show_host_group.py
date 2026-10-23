#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from http import HTTPStatus
from typing import Annotated

from cmk.gui.openapi.endpoints.utils import fetch_group
from cmk.gui.openapi.framework import (
    ApiContext,
    APIVersion,
    EndpointBehavior,
    EndpointDoc,
    EndpointHandler,
    EndpointMetadata,
    EndpointPermissions,
    PathParam,
    VersionedEndpoint,
)
from cmk.gui.openapi.framework.model.response import ApiResponse
from cmk.gui.openapi.restful_objects.constructors import object_href

from ._family import HOST_GROUP_FAMILY
from ._utils import host_group_etag, PERMISSIONS, serialize_host_group
from .models.response_models import HostGroupModel


def show_host_group_v1(
    api_context: ApiContext,
    name: Annotated[
        str,
        PathParam(description="The identifier name of the group.", example="pathname"),
    ],
) -> ApiResponse[HostGroupModel]:
    """Show a host group"""
    api_context.user.need_permission("wato.groups")
    group = fetch_group(name, "host")
    return ApiResponse(
        status_code=HTTPStatus.OK,
        body=serialize_host_group(api_context, group),
        etag=host_group_etag(group),
    )


ENDPOINT_SHOW_HOST_GROUP = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=object_href("host_group_config", "{name}"),
        link_relation="cmk/show",
        method="get",
    ),
    permissions=EndpointPermissions(required=PERMISSIONS),
    doc=EndpointDoc(family=HOST_GROUP_FAMILY.name),
    versions={APIVersion.V1: EndpointHandler(handler=show_host_group_v1)},
    behavior=EndpointBehavior(etag="output"),
)
