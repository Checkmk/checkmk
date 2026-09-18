#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Literal

from cmk.ccc.user import UserId
from cmk.gui.logged_in import user
from cmk.gui.openapi.api_endpoints.user_role.models.response_models import UserRoleModel
from cmk.gui.openapi.api_endpoints.user_role.utils import PERMISSIONS, serialize_role
from cmk.gui.openapi.framework import ApiContext
from cmk.gui.openapi.framework.api_config import APIVersion
from cmk.gui.openapi.framework.model import api_field, api_model
from cmk.gui.openapi.framework.model.base_models import DomainObjectCollectionModel, LinkModel
from cmk.gui.openapi.framework.versioned_endpoint import (
    EndpointDoc,
    EndpointHandler,
    EndpointMetadata,
    EndpointPermissions,
    VersionedEndpoint,
)
from cmk.gui.openapi.restful_objects.constructors import collection_href
from cmk.gui.permissions import load_dynamic_permissions, permission_registry
from cmk.gui.userdb import load_roles, UserRole
from cmk.gui.utils.roles import UserPermissions

from .endpoint_family import USER_ROLE_FAMILY


@api_model
class UserRoleCollectionModel(DomainObjectCollectionModel):
    domainType: Literal["user_role"] = api_field(
        description="The domain type of the objects in the collection",
        example="host_config",
    )
    value: list[UserRoleModel] = api_field(
        description="A list of user role objects",
        example=[],
    )


def list_user_roles_v1(api_context: ApiContext) -> UserRoleCollectionModel:
    """Show all user roles"""
    load_dynamic_permissions()
    user.need_permission("wato.users")
    user_permissions = UserPermissions(
        (roles := load_roles()),
        permission_registry,
        user_roles={
            UserId(user_id): user["roles"]
            for user_id, user in api_context.config.multisite_users.items()
        },
        default_user_profile_roles=api_context.config.default_user_profile["roles"],
    )
    return UserRoleCollectionModel(
        id="user_role",
        domainType="user_role",
        value=[
            serialize_role(UserRole(name=role_id, **role_spec), user_permissions)
            for role_id, role_spec in roles.items()
        ],
        links=[LinkModel.create("self", collection_href("user_role"))],
    )


ENDPOINT_LIST_USER_ROLES = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=collection_href("user_role"),
        link_relation=".../collection",
        method="get",
    ),
    permissions=EndpointPermissions(required=PERMISSIONS),
    doc=EndpointDoc(family=USER_ROLE_FAMILY.name),
    versions={APIVersion.V1: EndpointHandler(handler=list_user_roles_v1)},
)
