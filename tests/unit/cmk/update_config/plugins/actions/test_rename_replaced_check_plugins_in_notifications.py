#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from datetime import datetime
from logging import getLogger

import pytest

from cmk.ccc.user import UserId
from cmk.gui import userdb
from cmk.gui.config import active_config
from cmk.gui.userdb.store import load_users_uncached
from cmk.gui.watolib.notifications import NotificationRuleConfigFile
from cmk.update_config.lib import ExpiryVersion
from cmk.update_config.plugins.actions.rename_replaced_check_plugins_in_notifications import (
    RenameReplacedCheckPluginsInNotificationRules,
)


def _run_update_action() -> None:
    RenameReplacedCheckPluginsInNotificationRules(
        name="rename_replaced_check_plugins_in_notification_rules",
        title="Rename replaced check plug-ins in notification rules",
        sort_index=100,
        expiry_version=ExpiryVersion.NEVER,
    )(getLogger())


@pytest.mark.usefixtures("request_context")
def test_notification_rules_match_the_renamed_check_plugin() -> None:
    NotificationRuleConfigFile().save(
        [{"rule_id": "rule_1", "match_checktype": ["custom_query_metric_backend"]}],  # type: ignore[typeddict-item]
        pprint_value=False,
    )

    _run_update_action()

    match NotificationRuleConfigFile().load_for_reading():
        case [rule]:
            assert rule.get("match_checktype") == ["telemetry_custom_service"]
        case other:
            pytest.fail(f"Unexpected notification rules: {other!r}")


def test_personal_notification_rules_match_the_renamed_check_plugin(
    with_user: tuple[UserId, str],
) -> None:
    user_id, _password_of_user = with_user
    users = load_users_uncached(lock=True)
    users[user_id]["notification_rules"] = [
        {"rule_id": "rule_1", "match_checktype": ["custom_query_metric_backend"]}  # type: ignore[typeddict-item]
    ]
    userdb.save_users(
        users,
        userdb.get_user_attributes(active_config.wato_user_attrs),
        active_config.user_connections,
        now=datetime.now(),
        pprint_value=False,
        call_users_saved_hook=False,
    )

    _run_update_action()

    match load_users_uncached()[user_id].get("notification_rules"):
        case [rule]:
            assert rule.get("match_checktype") == ["telemetry_custom_service"]
        case other:
            pytest.fail(f"Unexpected personal notification rules: {other!r}")
