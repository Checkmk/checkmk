#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from logging import Logger
from uuid import uuid4

from cmk.utils.type_defs.notify import NotificationRuleID

from cmk.gui.watolib.notifications import load_notification_rules, save_notification_rules

from cmk.update_config.registry import update_action_registry, UpdateAction
from cmk.update_config.update_state import UpdateActionState


class UpdateRuleNotificationIDs(UpdateAction):
    def __call__(self, logger: Logger, update_action_state: UpdateActionState) -> None:
        notification_rules = load_notification_rules()
        for rule in notification_rules:
            if "rule_id" in rule:
                continue
            rule["rule_id"] = NotificationRuleID(str(uuid4()))
        save_notification_rules(notification_rules)


update_action_registry.register(
    UpdateRuleNotificationIDs(
        name="Update rule notification config",
        title="Add a rule_id to each notification rule",
        sort_index=80,  # I am not aware of any constrains
    )
)
