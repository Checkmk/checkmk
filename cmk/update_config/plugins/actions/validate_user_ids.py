#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from logging import Logger

from cmk.utils import tty
from cmk.utils.user import UserId

from cmk.gui.userdb import load_contacts, load_multisite_users, load_users

from cmk.update_config.registry import update_action_registry, UpdateAction
from cmk.update_config.update_state import UpdateActionState


class ValidateUserIds(UpdateAction):
    def __call__(self, logger: Logger, update_action_state: UpdateActionState) -> None:
        """
        Check if we can find UserIds that aren't valid in this version of Checkmk.

        This will try to call `load_users()` and, if that fails, explicitly test UserIds found in
        contacts.mk and users.mk. Even if there are no invalid users in these files, `load_users()`
        could fail due to invalid users in 'etc/htpasswd', 'etc/auth.serials`, or the folder names
        in 'var/check_mk/web' (which are also converted to UserIds).
        """
        try:
            load_users()
        except ValueError:
            err = """ERROR: Update aborted.
Incompatible user IDs have been found. Updating is not possible. See Werk #15182
for further information. """

            # The problematic users will hopefully be in contacts.mk or users.mk, so try to find
            # them there. They could, however, also just still hang around in htpasswd or in form
            # of a directory in 'var/check_mk/web'.
            def _is_valid(name: str) -> bool:
                try:
                    UserId.validate(name)
                    return True
                except ValueError:
                    return False

            if invalid_users := [
                user
                for user in set(list(load_contacts()) + list(load_multisite_users()))
                if not _is_valid(user)
            ]:
                err += "The following users are incompatible with Checkmk 2.2:\n  " + "\n  ".join(
                    invalid_users
                )
            else:
                err += """There are no invalid users in contacts.mk and users.mk.
Check 'etc/htpasswd', 'etc/auth.serials', and the directory names in
'var/check_mk/web'."""

            logger.error(f"{tty.red}{err}{tty.normal}")
            raise


update_action_registry.register(
    ValidateUserIds(
        name="validate_user_ids",
        title="Validate user IDs",
        # Run this validation before any plugin that deals with UserIds, as those would encounter
        # unexpected errors when UserIds cannot be created.
        # Currently the next to run is UpdateViews, which uses UserIds as view owners.
        sort_index=5,
        # Malformed user IDs would cause most other actions to fail as well.
        continue_on_failure=False,
    )
)
