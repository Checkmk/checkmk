#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Rename replaced check plug-ins in the conditions of notification rules

Notification rules can match on check plug-ins ("Match check types"). A rule naming a
check plug-in that has been renamed would silently stop matching its services.
"""

from datetime import datetime
from logging import Logger
from typing import override

from cmk.gui import userdb
from cmk.gui.config import active_config
from cmk.gui.userdb.store import load_users_uncached
from cmk.gui.watolib.notifications import NotificationRuleConfigFile
from cmk.update_config.internal import ExpiryVersion, UpdateAction
from cmk.update_config.plugins.lib.replaced_check_plugins import rename_matched_check_plugins
from cmk.update_config.registry import update_action_registry


class RenameReplacedCheckPluginsInNotificationRules(UpdateAction):
    @override
    def __call__(self, logger: Logger) -> None:
        rule_file = NotificationRuleConfigFile()
        rules = rule_file.load_for_modification()
        if rename_matched_check_plugins(rules):
            rule_file.save(rules, pprint_value=active_config.wato_pprint_config)

        # Uncached: the users are modified in place and must not leak into other actions
        users = load_users_uncached(lock=True)
        try:
            changed_users = [
                user_id
                for user_id, user_spec in users.items()
                if rename_matched_check_plugins(user_spec.get("notification_rules", []))
            ]
        except Exception:
            userdb.release_users_lock()
            raise

        if not changed_users:
            userdb.release_users_lock()
            return
        userdb.save_users(
            users,
            userdb.get_user_attributes(active_config.wato_user_attrs),
            active_config.user_connections,
            now=datetime.now(),
            pprint_value=active_config.wato_pprint_config,
            call_users_saved_hook=False,
            changed_users=changed_users,
        )


update_action_registry.register(
    RenameReplacedCheckPluginsInNotificationRules(
        name="rename_replaced_check_plugins_in_notification_rules",
        title="Rename replaced check plug-ins in notification rules",
        sort_index=100,  # no ordering constraints
        expiry_version=ExpiryVersion.NEVER,
    )
)
