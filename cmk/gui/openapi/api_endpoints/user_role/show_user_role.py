#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Annotated

from cmk.ccc.user import UserId
from cmk.gui.openapi.api_endpoints.user_role.utils import (
    PERMISSIONS,
    serialize_role,
)
from cmk.gui.openapi.framework import (
    ApiContext,
    APIVersion,
    PathParam,
)
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
from cmk.gui.permissions import permission_registry
from cmk.gui.userdb import load_roles
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.watolib.userroles import get_role, RoleID

from .endpoint_family import USER_ROLE_FAMILY
from .models.response_models import UserRoleModel


def show_user_role_v1(
    api_context: ApiContext,
    role_id: Annotated[
        RoleID,
        TypedPlainValidator(str, UserRoleIdConverter(permission_type="wato.users").should_exist),
        PathParam(description="An existing user role.", example="userx"),
    ],
) -> UserRoleModel:
    """Show a user role"""
    return serialize_role(
        get_role(role_id),
        UserPermissions(
            load_roles(),
            permission_registry,
            user_roles={
                UserId(user_id): user["roles"]
                for user_id, user in api_context.config.multisite_users.items()
            },
            default_user_profile_roles=api_context.config.default_user_profile["roles"],
        ),
    )


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
