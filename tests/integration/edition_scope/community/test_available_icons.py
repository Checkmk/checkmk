#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.views.icon import icon_and_action_registry


@pytest.mark.usefixtures("load_gui_plugins")
def test_builtin_icons_and_actions() -> None:
    expected_icons_and_actions = [
        "action_menu",
        "aggregation_checks",
        "aggregations",
        "check_manpage",
        "check_period",
        "crashed_check",
        "custom_action",
        "download_agent_output",
        "download_snmp_walk",
        "icon_image",
        "inventory",
        "inventory_history",
        "logwatch",
        "mkeventd",
        "network_topology",
        "notes",
        "parent_child_topology",
        "perfgraph",
        "prediction",
        "reschedule",
        "rule_editor",
        "stars",
        "status_acknowledged",
        "status_active_checks",
        "status_comments",
        "status_downtimes",
        "status_flapping",
        "status_notification_period",
        "status_notifications_enabled",
        "status_passive_checks",
        "status_service_period",
        "status_stale",
        "wato",
    ]

    assert sorted(icon_and_action_registry) == sorted(expected_icons_and_actions)
