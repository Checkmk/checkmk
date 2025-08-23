#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Annotated

from cmk.gui.openapi.api_endpoints.user_role.utils import PERMISSIONS, serialize_role
from cmk.gui.openapi.framework import PathParam
from cmk.gui.openapi.framework.api_config import APIVersion
from cmk.gui.openapi.framework.model.converter import (
    TypedPlainValidator,
    UserRoleIdConverter,
)
from cmk.gui.openapi.framework.versioned_endpoint import (
    EndpointDoc,
    EndpointHandler,
    EndpointMetadata,
    EndpointPermissions,
    VersionedEndpoint,
)
from cmk.gui.openapi.restful_objects.constructors import object_href
from cmk.gui.watolib.userroles import get_all_roles, get_role, RoleID

from .endpoint_family import USER_ROLE_FAMILY
from .models.response_models import UserRoleModel


def show_user_role_v1(
    role_id: Annotated[
        RoleID,
        TypedPlainValidator(str, UserRoleIdConverter(permission_type="wato.users").should_exist),
        PathParam(description="An existing user role.", example="userx"),
    ],
) -> UserRoleModel:
    """Show a user role"""
    return serialize_role(get_role(role_id), get_all_roles())


ENDPOINT_SHOW_USER_ROLE = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=object_href("user_role", "{role_id}"),
        link_relation="cmk/show",
        method="get",
    ),
    permissions=EndpointPermissions(required=PERMISSIONS),
    doc=EndpointDoc(family=USER_ROLE_FAMILY.name),
    versions={APIVersion.V1: EndpointHandler(handler=show_user_role_v1)},
)
