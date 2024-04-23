#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from __future__ import annotations

from enum import Enum
from typing import Literal, NewType

from pydantic import BaseModel, RootModel, ValidationError

from cmk.utils.config_validation_layer.validation_utils import ConfigValidationError


class BuiltInUserRoleValues(Enum):
    USER = "user"
    ADMIN = "admin"
    GUEST = "guest"
    AGENT_REGISTRATION = "agent_registration"


class UserRoleBase(BaseModel):
    alias: str
    permissions: dict[str, bool]


class CustomUserRole(UserRoleBase):
    builtin: Literal[False]
    basedon: BuiltInUserRoleValues


class BuiltInUserRole(UserRoleBase):
    builtin: Literal[True]


RoleID = NewType("RoleID", str)
UserRolesMap = RootModel[dict[RoleID, CustomUserRole | BuiltInUserRole]]


def validate_userroles(userroles: dict) -> None:
    try:
        UserRolesMap(userroles)
    except ValidationError as exc:
        raise ConfigValidationError(
            which_file="roles.mk",
            pydantic_error=exc,
            original_data=userroles,
        )


#
