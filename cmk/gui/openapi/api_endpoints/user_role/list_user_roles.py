#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from dataclasses import dataclass
from typing import Literal

from cmk.gui.logged_in import user
from cmk.gui.openapi.api_endpoints.user_role.models.response_models import (
    UserRoleModel,
)
from cmk.gui.openapi.api_endpoints.user_role.utils import PERMISSIONS, serialize_role
from cmk.gui.openapi.framework.api_config import APIVersion
from cmk.gui.openapi.framework.model import api_field
from cmk.gui.openapi.framework.model.base_models import DomainObjectCollectionModel, LinkModel
from cmk.gui.openapi.framework.versioned_endpoint import (
    EndpointDoc,
    EndpointHandler,
    EndpointMetadata,
    EndpointPermissions,
    VersionedEndpoint,
)
from cmk.gui.openapi.restful_objects.constructors import collection_href
from cmk.gui.permissions import load_dynamic_permissions
from cmk.gui.watolib.userroles import get_all_roles

from .endpoint_family import USER_ROLE_FAMILY


@dataclass(kw_only=True, slots=True)
class UserRoleCollectionModel(DomainObjectCollectionModel):
    domainType: Literal["user_role"] = api_field(
        description="The domain type of the objects in the collection",
        example="host_config",
    )
    value: list[UserRoleModel] = api_field(
        description="A list of user role objects",
        example=[],
    )


def list_user_roles_v1() -> UserRoleCollectionModel:
    """Show all user roles"""
    load_dynamic_permissions()
    user.need_permission("wato.users")
    return UserRoleCollectionModel(
        id="user_role",
        domainType="user_role",
        value=[serialize_role(role) for role in get_all_roles().values()],
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
