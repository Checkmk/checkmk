#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from datetime import datetime
from logging import Logger

from cmk.gui.plugins.userdb.utils import USER_SCHEME_SERIAL
from cmk.gui.type_defs import GlobalSettings
from cmk.gui.userdb import load_users, save_users, Users, UserSpec
from cmk.gui.watolib.global_settings import load_configuration_settings

from cmk.update_config.registry import update_action_registry, UpdateAction
from cmk.update_config.update_state import format_warning, UpdateActionState


def _flexible_notifications_active() -> bool:
    global_config: GlobalSettings = load_configuration_settings(full_config=True)
    return (
        "enable_rulebased_notifications" in global_config
        and not global_config["enable_rulebased_notifications"]
    )


def _update_user_attributes(users: Users, logger: Logger) -> Users:
    flexible_notifications_enabled = _flexible_notifications_active()
    if flexible_notifications_enabled:
        logger.warning(
            format_warning(
                "Rulebased notifications are not enabled in your configuration.\n\n"
                "Because flexible and plain email notifications are deprecated since \n"
                "version 1.5, this will remove such configuration from users.\n"
                "Affected users will be logged.\n"
                "One rulebased notification rule will be created within \n"
                '"Setup" - "Notifications" with the "HTML Email" plugin and contact \n'
                'selection "Notify all contacts of the notified host or service".\n\n'
                "Please adjust this rule by your needs.\n\n"
                "You can find more information about rule configuration here:\n"
                "https://docs.checkmk.com/latest/en/notifications.html"
            )
        )
    for user_id in users:
        user_spec = users[user_id]
        if flexible_notifications_enabled and user_spec.get("user_scheme_serial") == 0:
            _remove_flexible_notifications(user_spec)
            logger.warning("Removed notification configuration from user: %s" % user_id)
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
            _update_user_attributes(load_users(lock=True), logger),
            datetime.now(),
        )


update_action_registry.register(
    UpdateUserAttributes(
        name="user_attributes",
        title="User attributes",
        sort_index=19,
    )
)
