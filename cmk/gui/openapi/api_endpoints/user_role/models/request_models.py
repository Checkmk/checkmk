#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from dataclasses import dataclass
from typing import Annotated

from cmk.gui.openapi.framework.model import api_field, ApiOmitted
from cmk.gui.openapi.framework.model.converter import (
    TypedPlainValidator,
    UserRoleIdConverter,
)
from cmk.gui.watolib.userroles import RoleID


@dataclass(kw_only=True, slots=True)
class CreateUserRoleModel:
    role_id: Annotated[
        RoleID,
        TypedPlainValidator(str, UserRoleIdConverter(permission_type="wato.users").should_exist),
    ] = api_field(
        description="An existing userrole that you want to clone.",
        example="admin",
    )
    new_role_id: (
        Annotated[
            RoleID,
            TypedPlainValidator(
                str, UserRoleIdConverter(permission_type="wato.users").should_not_exist
            ),
        ]
        | ApiOmitted
    ) = api_field(
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
