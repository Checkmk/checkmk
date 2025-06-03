#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from tests.testlib import mocklogger

from cmk.gui.watolib.notifications import load_notification_rules, save_notification_rules

from cmk.update_config.plugins.actions.ensure_notification_rule_id import EnsureNotificationRuleIDs


def test_ensure_notification_rule_ids() -> None:
    save_notification_rules(
        [
            {
                "description": "Time Drift",
                "comment": "Bulk notifications sent to all users for NTP time drift issues.\n",
                "docu_url": "",
                "disabled": False,
                "allow_disable": False,
                "match_services": ["System Time"],
                "match_timeperiod": "WorkingHours",
                "match_service_event": ["rw", "rc", "wr", "wc", "cr", "cw", "x"],
                "contact_object": False,
                "contact_all": False,
                "contact_all_with_email": False,
                "contact_groups": ["all"],
                "notify_plugin": ("mail", None),
            },  # type: ignore[typeddict-item]
        ]
    )
    EnsureNotificationRuleIDs(
        name="ensure_notification_rule_ids",
        title="Ensure notification rule IDs",
        sort_index=49,
    )(mocklogger.MockLogger(), {})  # type: ignore[arg-type]

    for rule in load_notification_rules(lock=True):
        assert "rule_id" in rule, "Rule ID should be present in the notification rule"
