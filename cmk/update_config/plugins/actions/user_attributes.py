#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from datetime import datetime
from logging import Logger

from cmk.utils.log import VERBOSE

from cmk.gui.type_defs import Users
from cmk.gui.userdb import load_users, save_users

from cmk.update_config.registry import update_action_registry, UpdateAction
from cmk.update_config.update_state import UpdateActionState


class UpdateUserAttributes(UpdateAction):
    def __call__(self, logger: Logger, update_action_state: UpdateActionState) -> None:
        users = load_users(lock=True)
        save_users(
            _remove_deprecated_language_none(logger, users),
            datetime.now(),
        )


def _remove_deprecated_language_none(logger: Logger, users: Users) -> Users:
    """
    With version 2.2.0 we retyped user languages from None | str to str only.
    This function removes language params set to None in existing user configs.
    """
    changed_user_specs: bool = False
    for user_spec in users.values():
        if user_spec.get("language", -1) is None:
            changed_user_specs = True
            del user_spec["language"]

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
        sort_index=19,
    )
)
