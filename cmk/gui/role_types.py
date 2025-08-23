#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Literal, NotRequired, TypedDict

BuiltInUserRoleID = Literal["user", "admin", "guest", "agent_registration", "no_permissions"]


class UserRoleBase(TypedDict, total=True):
    alias: str
    permissions: dict[str, bool]
    two_factor: NotRequired[bool]


class CustomUserRole(UserRoleBase, total=True):
    builtin: Literal[False]
    basedon: BuiltInUserRoleID


class BuiltInUserRole(UserRoleBase, total=True):
    builtin: Literal[True]
