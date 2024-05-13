#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from datetime import datetime
from logging import Logger

from cmk.utils.log import VERBOSE
from cmk.utils.user import UserId

from cmk.gui.type_defs import Users, UserSpec
from cmk.gui.userdb import load_users, save_users

from cmk.update_config.registry import update_action_registry, UpdateAction


class UpdateUserAttributes(UpdateAction):
    def __call__(self, logger: Logger) -> None:
        users = load_users(lock=True, skip_validation=True)
        save_users(
            _update_user_attributes(logger, users),
            datetime.now(),
        )


def _update_disable_notifications(user_spec: UserSpec) -> None:
    disable_notifications = user_spec.get("disable_notifications")
    if isinstance(disable_notifications, bool):
        user_spec["disable_notifications"] = {"disable": True} if disable_notifications else {}


def _add_or_update_locked_attr(user_spec: UserSpec) -> None:
    """
    Until 2.3 the "locked" attribute was not set in all cases and could be
    bool | None
    """
    if "locked" not in user_spec:
        user_spec.setdefault("locked", False)
        return

    if user_spec.get("locked", False) is None:
        user_spec["locked"] = False
    return


def _add_alias(user_id: UserId, user_spec: UserSpec) -> None:
    """
    Until 2.4 the "alias" or full name could be missing for users created by LDAP.
    """
    user_spec.setdefault("alias", user_id)


def _update_user_attributes(logger: Logger, users: Users) -> Users:
    """
    With version 1.6.0 we deprecated boolean disable_notifications. SUP-17012

    With version 2.2.0 we retyped user languages from None | str to str only.
    This function removes language params set to None in existing user configs.
    """
    changed_user_specs: bool = False
    for user_id, user_spec in users.items():
        if user_spec.get("language", -1) is None:
            changed_user_specs = True
            del user_spec["language"]
        _update_disable_notifications(user_spec)
        _add_or_update_locked_attr(user_spec)
        _add_alias(user_id, user_spec)

    if changed_user_specs:
        logger.log(
            VERBOSE,
            "Removing deprecated user languages set to None. (The default remains English)",
        )
    return users


update_action_registry.register(
    UpdateUserAttributes(
        name="user_attributes",
        title="User attributes",
        # Run this validation before any plug-in that deals with users as those wouldn't be able
        # to load them.
        sort_index=2,
        # If users cannot be loaded, many other actions fail as well.
        continue_on_failure=False,
    )
)
