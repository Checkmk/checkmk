#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Annotated

from cmk.gui.openapi.framework.model import api_field, api_model, ApiOmitted
from cmk.gui.openapi.framework.model.converter import (
    PermissionsConverter,
    TypedPlainValidator,
    UserRoleIdConverter,
)
from cmk.gui.watolib.userroles import RoleID

_role_id_converter = UserRoleIdConverter(permission_type="wato.users")
ExistingRoleId = Annotated[
    RoleID,
    TypedPlainValidator(str, _role_id_converter.should_exist),
]
NewRoleId = Annotated[
    RoleID,
    TypedPlainValidator(str, _role_id_converter.should_not_exist),
]
BuiltInRoleId = Annotated[
    RoleID,
    TypedPlainValidator(str, _role_id_converter.should_be_builtin),
]


@api_model
class CreateUserRoleModel:
    role_id: ExistingRoleId = api_field(
        description="An existing userrole that you want to clone.",
        example="admin",
    )
    new_role_id: NewRoleId | ApiOmitted = api_field(
        description="The new role id for the newly created user role.",
        example="new_limited_permissions_userrole",
        default_factory=ApiOmitted,
    )
    new_alias: str | ApiOmitted = api_field(
        description="A new alias that you want to give to the newly created user role.",
        example="user_a",
        default_factory=ApiOmitted,
    )
    enforce_two_factor_authentication: bool | ApiOmitted = api_field(
        description="If enabled, all users with this role will be required to setup two"
        " factor authentication and will be logged out of any current sessions.",
        example=True,
        default_factory=ApiOmitted,
    )


@api_model
class EditUserRoleModel:
    new_role_id: NewRoleId | ApiOmitted = api_field(
        description="New role_id for the userrole that must be unique.",
        example="new_userrole_id",
        default_factory=ApiOmitted,
    )
    new_alias: str | ApiOmitted = api_field(
        description="New alias for the userrole that must be unique.",
        example="new_userrole_alias",
        default_factory=ApiOmitted,
    )
    new_basedon: BuiltInRoleId | ApiOmitted = api_field(
        description="A built-in user role that you want the user role to be based on.",
        example="guest",
        default_factory=ApiOmitted,
    )
    new_permissions: (
        Annotated[dict[str, str], TypedPlainValidator(dict, PermissionsConverter.validate)]
        | ApiOmitted
    ) = api_field(
        description="A map of permission names to their state.  The following values can be set: "
        "'yes' - the permission is active for this role."
        "'no' - the permission is deactivated for this role, even if it was active in the role it was based on."
        "'default' - takes the activation state from the role this role was based on. ",
        example={"general.edit_profile": "yes", "general.message": "no"},
        default_factory=ApiOmitted,
    )
    enforce_two_factor_authentication: bool | ApiOmitted = api_field(
        description="If enabled, all users with this role will be required to setup two"
        " factor authentication and will be logged out of any current sessions.",
        example=False,
        default_factory=ApiOmitted,
    )
