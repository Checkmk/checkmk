#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Literal

from cmk.gui.openapi.framework.model import api_field, api_model, ApiOmitted
from cmk.gui.openapi.framework.model.base_models import DomainObjectModel


@api_model
class UserRoleExtensionsModel:
    alias: str = api_field(
        description="The alias of the user role.",
    )
    permissions: list[str] = api_field(
        description="A list of permissions for the user role.",
    )
    builtin: bool = api_field(
        description="True if it's a built-in user role, otherwise False.",
    )
    enforce_two_factor_authentication: bool | ApiOmitted = api_field(
        description="If enabled, all users with this role will be required to setup two "
        "factor authentication and will be logged out of any current sessions.",
        default_factory=ApiOmitted,
    )
    basedon: str | ApiOmitted = api_field(
        description="The built-in user role id that the user role is based on.",
        default_factory=ApiOmitted,
    )


@api_model
class UserRoleModel(DomainObjectModel):
    domainType: Literal["user_role"] = api_field(
        description="The domain type of the object.",
    )
    extensions: UserRoleExtensionsModel = api_field(
        description="All the data and metadata of this user role."
    )
