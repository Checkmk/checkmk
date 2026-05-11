#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.logged_in import user
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
from cmk.gui.openapi.utils import FIELDS, ProblemException
from cmk.gui.type_defs import CustomHostAttrSpec
from cmk.gui.watolib.custom_attributes import (
    load_custom_attrs_from_mk_file,
    save_custom_attrs_to_mk_file,
    update_host_custom_attrs,
)

from ._family import CUSTOM_HOST_ATTR_FAMILY
from ._utils import attr_etag, DOMAIN_TYPE, RW_PERMISSIONS, serialize_attr
from .models.request_models import CreateCustomHostAttrModel
from .models.response_models import CustomHostAttrObject


def create_custom_host_attr_v1(
    api_context: ApiContext,
    body: CreateCustomHostAttrModel,
) -> ApiResponse[CustomHostAttrObject]:
    """Create a custom host attribute"""
    user.need_permission("wato.edit")
    user.need_permission("wato.custom_attributes")
    all_attrs = load_custom_attrs_from_mk_file(lock=True)
    if any(a["name"] == body.name for a in all_attrs["host"]):
        raise ProblemException(
            status=400,
            title="Name already in use",
            detail=f"An attribute with the name {body.name!r} already exists.",
            fields=FIELDS(
                {"body.name": {"msg": f"Name {body.name!r} is already in use", "input": body.name}}
            ),
        )
    new_attr = CustomHostAttrSpec(
        type="TextAscii",
        name=body.name,
        title=body.title,
        topic=body.topic,
        help=body.help,
        show_in_table=body.show_in_table,
        add_custom_macro=body.add_custom_macro,
    )
    all_attrs["host"].append(new_attr)
    save_custom_attrs_to_mk_file(all_attrs)
    update_host_custom_attrs(all_attrs["host"], pprint_value=api_context.config.wato_pprint_config)
    return ApiResponse(
        status_code=201,
        body=serialize_attr(new_attr),
        etag=attr_etag(new_attr),
    )


ENDPOINT_CREATE_CUSTOM_HOST_ATTR = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=collection_href(DOMAIN_TYPE),
        link_relation="cmk/create",
        method="post",
    ),
    behavior=EndpointBehavior(etag="output"),
    permissions=EndpointPermissions(required=RW_PERMISSIONS),
    doc=EndpointDoc(family=CUSTOM_HOST_ATTR_FAMILY.name),
    versions={APIVersion.V1: EndpointHandler(handler=create_custom_host_attr_v1)},
)
