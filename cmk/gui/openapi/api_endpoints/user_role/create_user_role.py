#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.logged_in import user
from cmk.gui.openapi.api_endpoints.user_role.utils import (
    RW_PERMISSIONS,
    serialize_role,
)
from cmk.gui.openapi.framework import (
    ApiContext,
    APIVersion,
    EndpointDoc,
    EndpointHandler,
    EndpointMetadata,
    EndpointPermissions,
    VersionedEndpoint,
)
from cmk.gui.openapi.restful_objects.constructors import collection_href
from cmk.gui.watolib.userroles import clone_role

from .endpoint_family import USER_ROLE_FAMILY
from .models.request_models import CreateUserRoleModel
from .models.response_models import UserRoleModel


def create_user_role_v1(api_context: ApiContext, body: CreateUserRoleModel) -> UserRoleModel:
    """Create a user role"""
    user.need_permission("wato.edit")

    return serialize_role(
        clone_role(
            role_id=body.role_id,
            new_role_id=body.new_role_id if isinstance(body.new_role_id, str) else None,
            new_alias=body.new_alias if isinstance(body.new_alias, str) else None,
            two_factor=body.enforce_two_factor_authentication
            if isinstance(body.enforce_two_factor_authentication, bool)
            else None,
            pprint_value=api_context.config.wato_pprint_config,
        )
    )


ENDPOINT_CREATE_USER_ROLE = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=collection_href("user_role"),
        link_relation="cmk/create",
        method="post",
    ),
    permissions=EndpointPermissions(required=RW_PERMISSIONS),
    doc=EndpointDoc(family=USER_ROLE_FAMILY.name),
    versions={APIVersion.V1: EndpointHandler(handler=create_user_role_v1)},
)
