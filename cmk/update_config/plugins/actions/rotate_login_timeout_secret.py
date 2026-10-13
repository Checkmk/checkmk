#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from logging import Logger
from typing import override

from cmk.update_config.lib import ExpiryVersion
from cmk.update_config.registry import update_action_registry, UpdateAction
from cmk.utils.local_secrets import LoginTimeoutSecret


class LoginTimeoutSecretRotation(UpdateAction):
    @override
    def __call__(self, logger: Logger) -> None:
        LoginTimeoutSecret().regenerate()


update_action_registry.register(
    LoginTimeoutSecretRotation(
        name="rotate_login_timeout_secret",
        title="Rotate login timeout secret",
        sort_index=101,  # should not matter when run
        expiry_version=ExpiryVersion.NEVER,
    )
)
