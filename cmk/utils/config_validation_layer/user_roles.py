#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from __future__ import annotations

from enum import Enum
from typing import Literal, NewType

from pydantic import BaseModel, model_validator


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
UserRolesMap = dict[RoleID, CustomUserRole | BuiltInUserRole]


class UserRoles(BaseModel):
    user: BuiltInUserRole
    admin: BuiltInUserRole
    guest: BuiltInUserRole
    agent_registration: BuiltInUserRole

    class Config:
        extra = "allow"

    @model_validator(mode="after")
    def validate_after(self) -> UserRoles:
        if self.model_extra is None:
            return self

        # Validate custom user roles and set them as attributes
        for field, value in self.model_extra.items():
            if isinstance(value, CustomUserRole):
                setattr(self, field, value)
            else:
                setattr(self, field, CustomUserRole(**value))

        return self

    def get_user_role_map(self) -> UserRolesMap:
        return {RoleID(k): getattr(self, k) for k in self.model_dump()}


def validate_userroles(userroles: dict) -> UserRolesMap:
    return UserRoles(**userroles).get_user_role_map()
