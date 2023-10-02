#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.fields.definitions import PermissionField, UserRoleID
from cmk.gui.fields.utils import BaseSchema

from cmk import fields


class CreateUserRole(BaseSchema):
    role_id = UserRoleID(
        required=True,
        description="Existing userrole that you want to clone.",
        example="admin",
        presence="should_exist",
    )
    new_role_id = UserRoleID(
        required=False,
        description="The new role id for the newly created user role.",
        example="limited_permissions_user",
        presence="should_not_exist",
    )
    new_alias = fields.String(
        required=False,
        description="A new alias that you want to give to the newly created user role.",
        example="user_a",
    )


class EditUserRole(BaseSchema):
    new_role_id = UserRoleID(
        required=False,
        description="New role_id for the userrole that must be unique.",
        example="new_userrole_id",
        presence="should_not_exist",
    )
    new_alias = fields.String(
        required=False,
        description="New alias for the userrole that must be unique.",
        example="new_userrole_alias",
    )
    new_basedon = UserRoleID(
        required=False,
        description="A built-in user role that you want the user role to be based on.",
        example="guest",
        presence="should_exist",
        userrole_type="should_be_builtin",
    )
    new_permissions = fields.Dict(
        keys=PermissionField(),
        values=fields.String(required=True, enum=["yes", "no", "default"]),
        required=False,
        example={"general.edit_profile": "yes", "general.message": "no"},
        description="A map of permission names to their state.  The following values can be set: "
        "'yes' - the permission is active for this role."
        "'no' - the permission is deactivated for this role, even if it was active in the role it was based on."
        "'default' - takes the activation state from the role this role was based on. ",
    )
