#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from http import HTTPStatus

from cmk.gui.openapi.endpoints.utils import fetch_group
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
from cmk.gui.watolib import groups

from ._family import HOST_GROUP_FAMILY
from ._utils import host_group_etag, make_pending_changes, RW_PERMISSIONS, serialize_host_group
from .models.request_models import CreateHostGroup
from .models.response_models import HostGroupModel


def create_host_group_v1(
    api_context: ApiContext, body: CreateHostGroup
) -> ApiResponse[HostGroupModel]:
    """Create a host group"""
    api_context.user.need_permission("wato.edit")
    api_context.user.need_permission("wato.groups")
    groups.add_group(
        body.name,
        "host",
        body.to_internal(),
        pprint_value=api_context.config.wato_pprint_config,
        pending_changes=make_pending_changes(api_context),
    )
    group = fetch_group(body.name, "host")
    return ApiResponse(
        status_code=HTTPStatus.OK,
        body=serialize_host_group(api_context, group),
        etag=host_group_etag(group),
    )


ENDPOINT_CREATE_HOST_GROUP = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=collection_href("host_group_config"),
        link_relation="cmk/create",
        method="post",
    ),
    permissions=EndpointPermissions(required=RW_PERMISSIONS),
    doc=EndpointDoc(family=HOST_GROUP_FAMILY.name),
    versions={APIVersion.V1: EndpointHandler(handler=create_host_group_v1)},
    behavior=EndpointBehavior(etag="output"),
)
