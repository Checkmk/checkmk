#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from datetime import datetime
from logging import Logger

from cmk.utils.local_secrets import AutomationUserSecret
from cmk.utils.user import UserId

from cmk.gui.type_defs import Users, UserSpec
from cmk.gui.userdb import load_users, save_users
from cmk.gui.utils.roles import AutomationUserFile

from cmk.update_config.plugins.actions.tag_conditions import get_tag_config, transform_host_tags
from cmk.update_config.registry import update_action_registry, UpdateAction


class UpdateUserAttributes(UpdateAction):
    def __call__(self, logger: Logger) -> None:
        users = load_users(lock=True)
        save_users(
            _update_user_attributes(logger, users),
            datetime.now(),
        )


def _add_alias(user_id: UserId, user_spec: UserSpec) -> None:
    """
    Until 2.4 the "alias" or full name could be missing for users created by LDAP.
    """
    user_spec.setdefault("alias", user_id)


def _add_roles(user_spec: UserSpec) -> None:
    """
    Until 2.4 the "roles" attribute could be missing for users.
    """
    user_spec.setdefault("roles", [])


def _migrate_automation_user(user_id: UserId) -> None:
    """
    Starting in 2.4 automation users no longer rely on the automation.secret file. Instead they have
    a boolean attribute in "automation_user.mk" to signify if a user has an "automation" user pseudo role.
    """
    secret = AutomationUserSecret(user_id)
    AutomationUserFile(user_id).save(secret.exists())


def _migrate_notification_rules(user_spec: UserSpec) -> None:
    """
    Until 2.4 the "tag" condition was in format list, from 2.4 on it's dict
    """
    if "notification_rules" not in user_spec:
        return

    tag_groups, aux_tag_list = get_tag_config()
    for rule in (notification_rules := user_spec.get("notification_rules", [])):
        if "match_hosttags" not in rule:
            continue

        if isinstance(host_tags := rule["match_hosttags"], dict):
            continue

        assert isinstance(host_tags, list)
        rule["match_hosttags"] = transform_host_tags(host_tags, tag_groups, aux_tag_list)

    user_spec["notification_rules"] = notification_rules


def _update_user_attributes(logger: Logger, users: Users) -> Users:
    for user_id, user_spec in users.items():
        _add_alias(user_id, user_spec)
        _migrate_automation_user(user_id)
        _add_roles(user_spec)
        _migrate_notification_rules(user_spec)
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
