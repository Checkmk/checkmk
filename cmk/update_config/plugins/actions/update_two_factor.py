#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from logging import Logger

from cmk.gui.userdb import load_two_factor_credentials, load_users
from cmk.gui.userdb.store import save_two_factor_credentials

from cmk.update_config.registry import update_action_registry, UpdateAction
from cmk.update_config.update_state import UpdateActionState


class UpdateExistingTwoFactor(UpdateAction):
    def __call__(self, logger: Logger, update_action_state: UpdateActionState) -> None:
        """
        Check if a user has an existing two_factor_credentials.mk file,

        Try validate that the user's 2fa file contains an entry for TOTP and if a KeyError is raised due to TOTP missing,
        add an empty totp dict.
        """
        num_users = 0
        for user in load_users():
            if "totp_credentials" not in (
                credentials := load_two_factor_credentials(user, lock=True)
            ):
                credentials["totp_credentials"] = {}
                save_two_factor_credentials(user, credentials)
                num_users += 1
        if num_users > 0:
            logger.info(
                "%d user(s) had their two factor file updated to allow for authenticator app usage",
                num_users,
            )


update_action_registry.register(
    UpdateExistingTwoFactor(
        name="update_two_factor",
        title="Update existing two factor",
        # This should not impact any other test as 2FA is not validated during updates
        sort_index=102,
        # If this fails, users will not be able to login if they have used 2fa configurations
        continue_on_failure=False,
    )
)
