#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from datetime import datetime
from logging import Logger

from cmk.gui.plugins.userdb.utils import USER_SCHEME_SERIAL
from cmk.gui.userdb import load_users, save_users, Users

from cmk.update_config.registry import update_action_registry, UpdateAction


def _add_user_scheme_serial(users: Users) -> Users:
    """Set attribute to detect with what cmk version the user was
    created. We start that with 2.0"""
    for user_id in users:
        users[user_id]["user_scheme_serial"] = USER_SCHEME_SERIAL
    return users


class UpdateUserAttributes(UpdateAction):
    def __call__(self, logger: Logger) -> None:
        save_users(
            _add_user_scheme_serial(load_users(lock=True)),
            datetime.now(),
        )


update_action_registry.register(
    UpdateUserAttributes(
        name="user_attributes",
        title="User attributes",
        sort_index=60,
    )
)
