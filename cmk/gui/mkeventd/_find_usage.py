#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

# It's OK to import centralized config load logic
import cmk.ec.export as ec  # pylint: disable=cmk-module-layer-violation

from cmk.gui.groups import GroupName
from cmk.gui.i18n import _
from cmk.gui.type_defs import GlobalSettings
from cmk.gui.watolib.config_domain_name import config_variable_registry
from cmk.gui.watolib.hosts_and_folders import folder_preserving_link


def find_usages_of_contact_group_in_mkeventd_notify_contactgroup(
    name: GroupName, global_config: GlobalSettings
) -> list[tuple[str, str]]:
    """Is the contactgroup used in mkeventd notify (if available)?"""
    used_in = []
    if "mkeventd_notify_contactgroup" in config_variable_registry:
        config_variable = config_variable_registry["mkeventd_notify_contactgroup"]
        domain = config_variable.domain()
        configured = global_config.get("mkeventd_notify_contactgroup")
        default_value = domain.default_globals()["mkeventd_notify_contactgroup"]
        if (configured and name == configured) or name == default_value:
            used_in.append(
                (
                    "%s" % (config_variable.valuespec().title()),
                    folder_preserving_link(
                        [("mode", "edit_configvar"), ("varname", "mkeventd_notify_contactgroup")]
                    ),
                )
            )
    return used_in


def find_usages_of_contact_group_in_ec_rules(
    name: str,
    _settings: GlobalSettings,
    rule_packs: Sequence[ec.ECRulePack] | None = None,
) -> list[tuple[str, str]]:
    """Is the contactgroup used in an eventconsole rule?"""
    used_in: list[tuple[str, str]] = []
    if rule_packs is None:
        rule_packs = ec.load_rule_packs()
    for pack in rule_packs:
        for nr, rule in enumerate(pack.get("rules", [])):
            if name in rule.get("contact_groups", {}).get("groups", []):
                used_in.append(
                    (
                        "{}: {}".format(_("Event console rule"), rule["id"]),
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
    rule_packs = ec.load_rule_packs()
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
                used_in.append((_("Event console rule"), url))
    return used_in
