#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from logging import Logger
from typing import override

from cmk.gui.watolib.notifications import NotificationRuleConfigFile
from cmk.gui.watolib.sample_config import new_notification_rule_id

from cmk.update_config.registry import update_action_registry, UpdateAction


class EnsureNotificationRuleIDs(UpdateAction):
    @override
    def __call__(self, logger: Logger) -> None:
        nr_config_file = NotificationRuleConfigFile()
        notification_rules = nr_config_file.load_for_modification()
        for rule in notification_rules:
            if "rule_id" not in rule:
                rule["rule_id"] = new_notification_rule_id()
        nr_config_file.save(cfg=notification_rules)


update_action_registry.register(
    EnsureNotificationRuleIDs(
        name="ensure_notification_rule_ids",
        title="Ensure notification rule IDs",
        sort_index=49,
    )
)
