#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Annotated

from cmk.gui.config import active_config
from cmk.gui.logged_in import user
from cmk.gui.openapi.api_endpoints.user_role.utils import (
    RW_PERMISSIONS,
    serialize_role,
)
from cmk.gui.openapi.framework import (
    APIVersion,
    EndpointDoc,
    EndpointHandler,
    EndpointMetadata,
    EndpointPermissions,
    PathParam,
    VersionedEndpoint,
)
from cmk.gui.openapi.restful_objects.constructors import object_href
from cmk.gui.openapi.utils import RestAPIRequestGeneralException
from cmk.gui.permissions import load_dynamic_permissions
from cmk.gui.userdb import UserRole
from cmk.gui.watolib.userroles import (
    get_role,
    RoleID,
    update_permissions,
    update_role,
    validate_new_alias,
    validate_new_roleid,
)

from .endpoint_family import USER_ROLE_FAMILY
from .models.request_models import EditUserRoleModel, ExistingRoleId
from .models.response_models import UserRoleModel


def _check_and_update_new_alias(
    existing_userrole_copy: UserRole,
    userrole_edits: EditUserRoleModel,
) -> None:
    if isinstance(userrole_edits.new_alias, str):
        try:
            validate_new_alias(existing_userrole_copy.alias, userrole_edits.new_alias)
        except ValueError as e:
            raise RestAPIRequestGeneralException(
                status=400,
                title="Invalid alias",
                detail=str(e),
            )
        existing_userrole_copy.alias = userrole_edits.new_alias


def _check_and_update_new_role_id(
    existing_userrole_copy: UserRole,
    userrole_edits: EditUserRoleModel,
) -> None:
    if isinstance(userrole_edits.new_role_id, str):
        try:
            validate_new_roleid(existing_userrole_copy.name, userrole_edits.new_role_id)
        except ValueError as e:
            raise RestAPIRequestGeneralException(
                status=400,
                title="Invalid role ID",
                detail=str(e),
            )
        existing_userrole_copy.name = userrole_edits.new_role_id


def edit_user_role_v1(
    role_id: Annotated[
        ExistingRoleId,
        PathParam(description="An existing user role.", example="userx"),
    ],
    body: EditUserRoleModel,
) -> UserRoleModel:
    """Edit a user role"""
    load_dynamic_permissions()
    user.need_permission("wato.edit")
    existing_userrole_copy: UserRole = get_role(role_id)

    _check_and_update_new_alias(existing_userrole_copy, body)
    _check_and_update_new_role_id(existing_userrole_copy, body)

    if isinstance(body.new_basedon, str):
        existing_userrole_copy.basedon = body.new_basedon

    if isinstance(body.enforce_two_factor_authentication, bool):
        existing_userrole_copy.two_factor = body.enforce_two_factor_authentication

    if isinstance(body.new_permissions, dict):
        update_permissions(existing_userrole_copy, iter(body.new_permissions.items()))

    update_role(
        role=existing_userrole_copy,
        old_roleid=role_id,
        new_roleid=RoleID(existing_userrole_copy.name),
        pprint_value=active_config.wato_pprint_config,
    )

    return serialize_role(existing_userrole_copy)


ENDPOINT_EDIT_USER_ROLE = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=object_href("user_role", "{role_id}"),
        link_relation="cmk/update",
        method="put",
    ),
    permissions=EndpointPermissions(required=RW_PERMISSIONS),
    doc=EndpointDoc(family=USER_ROLE_FAMILY.name),
    versions={APIVersion.UNSTABLE: EndpointHandler(handler=edit_user_role_v1)},
)
