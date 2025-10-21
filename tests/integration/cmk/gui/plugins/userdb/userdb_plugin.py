#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"
# mypy: disable-error-code="type-arg"

from collections.abc import Sequence

from cmk.ccc.user import UserId
from cmk.crypto.password import Password
from cmk.gui.type_defs import UserSpec
from cmk.gui.user_connection_config_types import UserConnectionConfig
from cmk.gui.userdb import (
    CheckCredentialsResult,
    user_connector_registry,
    UserAttribute,
    UserConnector,
)


@user_connector_registry.register
class TestConnector(UserConnector):
    @classmethod
    def type(cls):
        return "test"

    @classmethod
    def title(cls):
        return "test"

    @classmethod
    def short_title(cls):
        return "test"

    def is_enabled(self) -> bool:
        return False

    def check_credentials(
        self,
        user_id: UserId,
        password: Password,
        user_attributes: Sequence[tuple[str, UserAttribute]],
        user_connections: Sequence[UserConnectionConfig],
        default_user_profile: UserSpec,
    ) -> CheckCredentialsResult:
        return None
