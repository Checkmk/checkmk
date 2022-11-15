#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from datetime import datetime
from logging import Logger

from cmk.gui.plugins.userdb.utils import USER_SCHEME_SERIAL
from cmk.gui.userdb import load_users, save_users, Users, UserSpec
from cmk.gui.watolib.global_settings import load_configuration_settings

from cmk.update_config.registry import update_action_registry, UpdateAction
from cmk.update_config.update_state import UpdateActionState


def _update_user_attributes(users: Users) -> Users:
    active_flexible_notifications: bool = not load_configuration_settings().get(
        "enable_rulebased_notifications", False
    )
    for user_id in users:
        user_spec = users[user_id]
        if active_flexible_notifications and user_spec.get("user_scheme_serial") == 0:
            _remove_flexible_notifications(user_spec)
        _add_user_scheme_serial(user_spec)
    return users


def _add_user_scheme_serial(user: UserSpec) -> None:
    """Set attribute to detect with what cmk version the user was
    created. We start that with 2.0"""
    user["user_scheme_serial"] = USER_SCHEME_SERIAL


def _remove_flexible_notifications(user: UserSpec) -> None:
    """Remove flexible notification configuration from users (version 2.2)"""
    for key in [
        "notifications_enabled",
        "notification_period",
        "host_notification_options",
        "service_notification_options",
        "notification_method",
    ]:
        if not key in user:
            continue

        del user[key]  # type: ignore


class UpdateUserAttributes(UpdateAction):
    def __call__(self, logger: Logger, update_action_state: UpdateActionState) -> None:
        save_users(
            _update_user_attributes(load_users(lock=True)),
            datetime.now(),
        )


update_action_registry.register(
    UpdateUserAttributes(
        name="user_attributes",
        title="User attributes",
        sort_index=60,
    )
)
