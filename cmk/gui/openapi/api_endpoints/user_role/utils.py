#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.openapi.framework.model.constructors import generate_links
from cmk.gui.userdb import UserRole
from cmk.gui.utils import permission_verification as permissions
from cmk.gui.utils.roles import UserPermissions

from .models.response_models import UserRoleExtensionsModel, UserRoleModel

PERMISSIONS = permissions.Perm("wato.users")
RW_PERMISSIONS = permissions.AllPerm(
    [
        permissions.Perm("wato.edit"),
        PERMISSIONS,
    ]
)


def serialize_role(role: UserRole, user_permissions: UserPermissions) -> UserRoleModel:
    user_role_model = UserRoleModel(
        domainType="user_role",
        id=role.name,
        title=role.alias,
        extensions=UserRoleExtensionsModel(
            alias=role.alias,
            permissions=user_permissions.get_role_permissions()[role.name],
            builtin=role.builtin,
            enforce_two_factor_authentication=role.two_factor,
        ),
        links=generate_links(
            domain_type="user_role", identifier=role.name, deletable=not role.builtin
        ),
    )
    if role.basedon:
        user_role_model.extensions.basedon = role.basedon
    return user_role_model
