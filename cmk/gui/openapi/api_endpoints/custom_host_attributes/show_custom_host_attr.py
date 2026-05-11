#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Annotated

from cmk.gui.logged_in import user
from cmk.gui.openapi.api_endpoints.custom_host_attributes._family import CUSTOM_HOST_ATTR_FAMILY
from cmk.gui.openapi.api_endpoints.custom_host_attributes._utils import (
    attr_etag,
    DOMAIN_TYPE,
    find_attr_or_raise,
    PERMISSIONS,
    serialize_attr,
)
from cmk.gui.openapi.api_endpoints.custom_host_attributes.models.response_models import (
    CustomHostAttrObject,
)
from cmk.gui.openapi.framework import (
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


def show_custom_host_attr_v1(
    name: Annotated[
        str,
        PathParam(
            description="The name of the custom host attribute.",
            example="coordinates",
        ),
    ],
) -> ApiResponse[CustomHostAttrObject]:
    """Show a custom host attribute"""
    user.need_permission("wato.custom_attributes")
    attr, _all_attrs = find_attr_or_raise(name, lock=False)
    return ApiResponse(
        status_code=200,
        body=serialize_attr(attr),
        etag=attr_etag(attr),
    )


ENDPOINT_SHOW_CUSTOM_HOST_ATTR = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=object_href(DOMAIN_TYPE, "{name}"),
        link_relation="cmk/show",
        method="get",
    ),
    behavior=EndpointBehavior(etag="output"),
    permissions=EndpointPermissions(required=PERMISSIONS),
    doc=EndpointDoc(family=CUSTOM_HOST_ATTR_FAMILY.name),
    versions={APIVersion.V1: EndpointHandler(handler=show_custom_host_attr_v1)},
)
