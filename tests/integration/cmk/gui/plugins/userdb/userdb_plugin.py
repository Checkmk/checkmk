#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.utils.crypto.password import Password
from cmk.utils.type_defs import UserId

from cmk.gui.plugins.userdb.utils import (
    CheckCredentialsResult,
    user_connector_registry,
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

    def check_credentials(self, user_id: UserId, password: Password) -> CheckCredentialsResult:
        return None
