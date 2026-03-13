#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from logging import Logger

from cmk.utils.crypto.secrets import AuthenticationSecret

from cmk.update_config.registry import update_action_registry, UpdateAction
from cmk.update_config.update_state import UpdateActionState


class AuthSecretRotation(UpdateAction):
    def __call__(self, logger: Logger, update_action_state: UpdateActionState) -> None:
        AuthenticationSecret().regenerate()


update_action_registry.register(
    AuthSecretRotation(
        name="rotate_auth_secret",
        title="Rotate auth secret",
        sort_index=100,  # I am not aware of any constrains
    )
)
