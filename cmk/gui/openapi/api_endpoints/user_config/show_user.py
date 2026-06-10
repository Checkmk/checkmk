#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Annotated

from cmk.ccc.user import UserId
from cmk.gui.logged_in import user
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
from cmk.gui.openapi.framework.model.converter import TypedPlainValidator
from cmk.gui.openapi.framework.model.response import ApiResponse
from cmk.gui.openapi.restful_objects.constructors import object_href
from cmk.gui.openapi.shared_endpoint_families.user_config import USER_CONFIG_FAMILY

from ._utils import load_user, PERMISSIONS, serialize_user, user_etag, username_should_exist
from .models.response_models import UserObject


def show_user_v1(
    username: Annotated[
        Annotated[UserId, TypedPlainValidator(str, username_should_exist)],
        PathParam(description="An unique username for the user", example="cmkuser"),
    ],
) -> ApiResponse[UserObject]:
    """Show a user"""
    user.need_permission("wato.users")
    user_spec = load_user(username)
    return ApiResponse(
        status_code=200,
        body=serialize_user(username, user_spec),
        etag=user_etag(user_spec),
    )


ENDPOINT_SHOW_USER = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=object_href("user_config", "{username}"),
        link_relation="cmk/show",
        method="get",
    ),
    behavior=EndpointBehavior(etag="output"),
    permissions=EndpointPermissions(required=PERMISSIONS),
    doc=EndpointDoc(family=USER_CONFIG_FAMILY.name),
    versions={APIVersion.V1: EndpointHandler(handler=show_user_v1)},
)
