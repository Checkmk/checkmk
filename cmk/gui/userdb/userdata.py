#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from dataclasses import dataclass
from typing import Self

from cmk.ccc.user import UserId
from cmk.gui.type_defs import UserSpec


@dataclass
class UserData:
    """Represents user data stored on disk.

    This class is WIP with CMK-16814; do not use it yet.
    """

    user_id: UserId
    alias: str  # aka "Full name"
    email: str | None
    pager: str | None
    contactgroups: list[str]

    def to_userspec(self) -> UserSpec:
        return UserSpec(
            user_id=self.user_id,
            alias=self.alias,
            email=self.email or "",
            pager=self.pager or "",
            contactgroups=self.contactgroups,
        )

    @classmethod
    def from_userspec(cls, userspec: UserSpec) -> Self:
        return cls(
            user_id=userspec["user_id"],
            alias=userspec["alias"],
            email=userspec.get("email"),
            pager=userspec.get("pager"),
            contactgroups=userspec.get("contactgroups", []),
        )
