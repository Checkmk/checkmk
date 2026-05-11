#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Annotated

from cmk.gui.logged_in import user
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
from cmk.gui.watolib.custom_attributes import (
    save_custom_attrs_to_mk_file,
    update_host_custom_attrs,
)

from ._family import CUSTOM_HOST_ATTR_FAMILY
from ._utils import attr_etag, DOMAIN_TYPE, find_attr_or_raise, RW_PERMISSIONS, serialize_attr
from .models.request_models import UpdateCustomHostAttrModel
from .models.response_models import CustomHostAttrObject


def update_custom_host_attr_v1(
    api_context: ApiContext,
    body: UpdateCustomHostAttrModel,
    name: Annotated[
        str,
        PathParam(
            description="The name of the custom host attribute.",
            example="coordinates",
        ),
    ],
) -> ApiResponse[CustomHostAttrObject]:
    """Update a custom host attribute"""
    user.need_permission("wato.edit")
    user.need_permission("wato.custom_attributes")
    attr, all_attrs = find_attr_or_raise(name, lock=True)
    if api_context.etag.enabled:
        api_context.etag.verify(attr_etag(attr))
    if body.title is not None:
        attr["title"] = body.title
    if body.topic is not None:
        attr["topic"] = body.topic
    if body.help is not None:
        attr["help"] = body.help
    if body.show_in_table is not None:
        attr["show_in_table"] = body.show_in_table
    if body.add_custom_macro is not None:
        attr["add_custom_macro"] = body.add_custom_macro
    save_custom_attrs_to_mk_file(all_attrs)
    update_host_custom_attrs(all_attrs["host"], pprint_value=api_context.config.wato_pprint_config)
    return ApiResponse(
        status_code=200,
        body=serialize_attr(attr),
        etag=attr_etag(attr),
    )


ENDPOINT_UPDATE_CUSTOM_HOST_ATTR = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=object_href(DOMAIN_TYPE, "{name}"),
        link_relation=".../update",
        method="put",
    ),
    behavior=EndpointBehavior(etag="both"),
    permissions=EndpointPermissions(required=RW_PERMISSIONS),
    doc=EndpointDoc(family=CUSTOM_HOST_ATTR_FAMILY.name),
    versions={APIVersion.V1: EndpointHandler(handler=update_custom_host_attr_v1)},
)
