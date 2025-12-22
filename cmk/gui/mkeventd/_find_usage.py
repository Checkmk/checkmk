#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

# It's OK to import centralized config load logic
import cmk.ec.export as ec  # astrein: disable=cmk-module-layer-violation
import cmk.utils.paths
from cmk.gui.groups import GroupName
from cmk.gui.i18n import _
from cmk.gui.type_defs import GlobalSettings
from cmk.gui.watolib.hosts_and_folders import folder_preserving_link


class UsagesOfContactGroupInMkeventdNotifyContactGroupFinder:
    __name__ = "find_usages_of_contact_group_in_mkeventd_notify_contactgroup"

    def __init__(
        self,
        mkeventd_notify_contactgroup_settings_title: str,
        mkevent_notify_contactgroup_default: GroupName,
    ) -> None:
        self._title = mkeventd_notify_contactgroup_settings_title
        self._default = mkevent_notify_contactgroup_default

    def __call__(self, name: GroupName, global_config: GlobalSettings) -> list[tuple[str, str]]:
        if (name == global_config.get("mkeventd_notify_contactgroup")) or (name == self._default):
            return [
                (
                    self._title,
                    folder_preserving_link(
                        [
                            ("mode", "edit_configvar"),
                            ("varname", "mkeventd_notify_contactgroup"),
                        ]
                    ),
                )
            ]
        return []


def find_usages_of_contact_group_in_ec_rules(
    name: str,
    _settings: GlobalSettings,
    rule_packs: Sequence[ec.ECRulePack] | None = None,
) -> list[tuple[str, str]]:
    """Is the contactgroup used in an eventconsole rule?"""
    used_in: list[tuple[str, str]] = []
    if rule_packs is None:
        rule_packs = ec.load_rule_packs(ec.create_paths(cmk.utils.paths.omd_root))
    for pack in rule_packs:
        for nr, rule in enumerate(pack.get("rules", [])):
            if name in rule.get("contact_groups", {}).get("groups", []):
                used_in.append(
                    (
                        "{}: {}".format(_("Event Console rule"), rule["id"]),
                        folder_preserving_link(
                            [
                                ("mode", "mkeventd_edit_rule"),
                                ("edit", nr),
                                ("rule_pack", pack["id"]),
                            ]
                        ),
                    )
                )
    return used_in


def find_timeperiod_usage_in_ec_rules(time_period_name: str) -> list[tuple[str, str]]:
    used_in: list[tuple[str, str]] = []
    rule_packs = ec.load_rule_packs(ec.create_paths(cmk.utils.paths.omd_root))
    for rule_pack in rule_packs:
        for rule_index, rule in enumerate(rule_pack["rules"]):
            if rule.get("match_timeperiod") == time_period_name:
                url = folder_preserving_link(
                    [
                        ("mode", "mkeventd_edit_rule"),
                        ("edit", rule_index),
                        ("rule_pack", rule_pack["id"]),
                    ]
                )
                used_in.append((_("Event Console rule"), url))
    return used_in
