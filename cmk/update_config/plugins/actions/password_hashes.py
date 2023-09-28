#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from logging import Logger

from cmk.utils.crypto.password_hashing import is_unsupported_legacy_hash

from cmk.gui.userdb import is_automation_user, load_users, Users

from cmk.update_config.registry import update_action_registry, UpdateAction
from cmk.update_config.update_state import format_warning, UpdateActionState


class CheckPasswordHashes(UpdateAction):
    """
    Inform admins about users that won't be able to log in due to unsupported password hashes.

    Support for older password hashing schemes has been removed. Since Werk #14391 old hashes
    were either automatically updated upon login or users were asked to choose new passwords,
    depending on how old and insecure their hashes were.
    If a user has not logged in at all since Werk #14391 it is possible that they still use the
    old hashing scheme. These user will not be able to log in after the update, since support for
    these schemes has been removed.

    As a result, their passwords have to be manually reset by the admin, either via WATO or using
    cmk-passwd.
    This check informs admins about affected users.
    """

    def __call__(self, logger: Logger, update_action_state: UpdateActionState) -> None:
        users: Users = load_users()
        if unsupported := [
            user_id
            for user_id in users
            if (
                (users[user_id].get("connector") == "htpasswd")
                # Automation users' password hashes are irrelevant, as they are not used for login.
                and not is_automation_user(users[user_id])
                and (pw := users[user_id].get("password"))
                and is_unsupported_legacy_hash(pw)
            )
        ]:
            explanation = """Users with outdated, no longer supported password hashes have been found. These users will be unable to log in.
Please manually reset these users' passwords either in Setup > Users or on the commandline using the cmk-passwd command.
The following users are affected:
"""
            logger.warning(format_warning(explanation + "\n".join(unsupported)))


update_action_registry.register(
    CheckPasswordHashes(
        name="check_password_hashes",
        title="Check for incompatible password hashes",
        sort_index=100,  # can run whenever
    )
)
