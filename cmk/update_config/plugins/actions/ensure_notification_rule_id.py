#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from logging import Logger
from typing import override

from cmk.gui.watolib.notifications import load_notification_rules, save_notification_rules
from cmk.gui.watolib.sample_config import new_notification_rule_id

from cmk.update_config.registry import update_action_registry, UpdateAction
from cmk.update_config.update_state import UpdateActionState


class EnsureNotificationRuleIDs(UpdateAction):
    @override
    def __call__(self, logger: Logger, update_action_state: UpdateActionState) -> None:
        notification_rules = load_notification_rules(lock=True)
        for rule in notification_rules:
            if "rule_id" not in rule:
                rule["rule_id"] = new_notification_rule_id()
        save_notification_rules(rules=notification_rules)


update_action_registry.register(
    EnsureNotificationRuleIDs(
        name="ensure_notification_rule_ids",
        title="Ensure notification rule IDs",
        sort_index=49,
    )
)
