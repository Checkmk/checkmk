#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.checkengine.plugins import CheckPluginName
from cmk.update_config.plugins.lib.replaced_check_plugins import rename_matched_check_plugins

_RENAMED_PLUGINS = {CheckPluginName("old_plugin"): CheckPluginName("new_plugin")}


def test_event_rules_match_the_renamed_check_plugin() -> None:
    rules: list[dict[str, object]] = [
        {"match_checktype": ["old_plugin", "other_plugin"]},
        {"match_checktype": ["old_plugin"]},
    ]

    assert rename_matched_check_plugins(rules, _RENAMED_PLUGINS)

    assert rules == [
        {"match_checktype": ["new_plugin", "other_plugin"]},
        {"match_checktype": ["new_plugin"]},
    ]


def test_event_rules_without_replaced_check_plugins_are_left_alone() -> None:
    rule: dict[str, object] = {"match_checktype": ["other_plugin"]}

    assert not rename_matched_check_plugins([rule], _RENAMED_PLUGINS)

    assert rule == {"match_checktype": ["other_plugin"]}
