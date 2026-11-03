#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.checkengine.plugins import CheckPluginName, SectionName
from cmk.plugins.ups.agent_based.ups_eaton_environment import (
    check_plugin_ups_eaton_environment,
    snmp_section_ups_eaton_environment,
)
from cmk.update_config.plugins.lib.replaced_check_plugins import (
    ALL_REPLACED_CHECK_PLUGINS,
    rename_matched_check_plugins,
)
from cmk.update_config.plugins.lib.rulesets import REPLACED_SNMP_SECTIONS


def test_misspelled_eaton_environment_services_are_taken_over_by_the_renamed_plugin() -> None:
    """The update rewrites autochecks and rule values by this name, plug-in or not: a wrong one
    makes the services vanish until rediscovery."""
    assert ALL_REPLACED_CHECK_PLUGINS[CheckPluginName("ups_eaton_enviroment")] == (
        CheckPluginName(check_plugin_ups_eaton_environment.name)
    )


def test_misspelled_eaton_environment_section_rules_are_taken_over_by_the_renamed_section() -> None:
    """The update rewrites the SNMP section rules by this name, section or not: a wrong one makes
    the rules silently stop applying."""
    assert REPLACED_SNMP_SECTIONS[SectionName("ups_eaton_enviroment")] == (
        SectionName(snmp_section_ups_eaton_environment.name)
    )


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
