#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Tuple as _Tuple

import cmk.utils.store as store
import cmk.utils.version as cmk_version
from cmk.utils.type_defs import EventRule, timeperiod_spec_alias, TimeperiodSpec, TimeperiodSpecs

import cmk.ec.export as ec  # pylint: disable=cmk-module-layer-violation

import cmk.gui.watolib as watolib
from cmk.gui import userdb
from cmk.gui.globals import config
from cmk.gui.hooks import request_memoize
from cmk.gui.i18n import _
from cmk.gui.valuespec import DropdownChoice
from cmk.gui.watolib import changes as _changes
from cmk.gui.watolib.hosts_and_folders import folder_preserving_link
from cmk.gui.watolib.notifications import load_notification_rules
from cmk.gui.watolib.utils import wato_root_dir

try:
    import cmk.gui.cee.plugins.wato.alert_handling as alert_handling
except ImportError:
    alert_handling = None  # type: ignore[assignment]

TimeperiodUsage = _Tuple[str, str]


class TimePeriodNotFoundError(KeyError):
    pass


class TimePeriodAlreadyExistsError(KeyError):
    pass


class TimePeriodBuiltInError(Exception):
    pass


class TimePeriodInUseError(Exception):
    def __init__(self, usages: list[TimeperiodUsage]) -> None:
        super().__init__()
        self.usages = usages


def builtin_timeperiods() -> TimeperiodSpecs:
    return {
        "24X7": {
            "alias": _("Always"),
            "monday": [("00:00", "24:00")],
            "tuesday": [("00:00", "24:00")],
            "wednesday": [("00:00", "24:00")],
            "thursday": [("00:00", "24:00")],
            "friday": [("00:00", "24:00")],
            "saturday": [("00:00", "24:00")],
            "sunday": [("00:00", "24:00")],
        }
    }


@request_memoize()
def load_timeperiods() -> TimeperiodSpecs:
    timeperiods = store.load_from_mk_file(wato_root_dir() + "timeperiods.mk", "timeperiods", {})
    timeperiods.update(builtin_timeperiods())
    return timeperiods


def load_timeperiod(name: str) -> TimeperiodSpec:
    try:
        timeperiod = load_timeperiods()[name]
    except KeyError:
        raise TimePeriodNotFoundError
    return timeperiod


def delete_timeperiod(name: str) -> None:
    if name in builtin_timeperiods():
        raise TimePeriodBuiltInError()
    time_periods = load_timeperiods()
    if name not in time_periods:
        raise TimePeriodNotFoundError
    if usages := find_usages_of_timeperiod(name):
        raise TimePeriodInUseError(usages=usages)
    del time_periods[name]
    save_timeperiods(time_periods)
    _changes.add_change("edit-timeperiods", _("Deleted time period %s") % name)


def save_timeperiods(timeperiods: TimeperiodSpecs) -> None:
    store.mkdir(wato_root_dir())
    store.save_to_mk_file(
        wato_root_dir() + "timeperiods.mk",
        "timeperiods",
        _filter_builtin_timeperiods(timeperiods),
        pprint_value=config.wato_pprint_config,
    )
    load_timeperiods.cache_clear()


def modify_timeperiod(name: str, timeperiod: TimeperiodSpec) -> None:  # type: ignore[no-untyped-def]
    existing_timeperiods = load_timeperiods()
    if name not in existing_timeperiods:
        raise TimePeriodNotFoundError()

    existing_timeperiods[name] = timeperiod
    save_timeperiods(existing_timeperiods)
    _changes.add_change("edit-timeperiods", _("Modified time period %s") % name)


def create_timeperiod(name: str, timeperiod: TimeperiodSpec) -> None:  # type: ignore[no-untyped-def]
    existing_timeperiods = load_timeperiods()
    if name in existing_timeperiods:
        raise TimePeriodAlreadyExistsError()

    existing_timeperiods[name] = timeperiod
    save_timeperiods(existing_timeperiods)
    _changes.add_change("edit-timeperiods", _("Created new time period %s") % name)


def verify_timeperiod_name_exists(name):
    existing_timperiods = load_timeperiods()
    return name in existing_timperiods


def _filter_builtin_timeperiods(timeperiods: TimeperiodSpecs) -> TimeperiodSpecs:
    builtin_keys = set(builtin_timeperiods().keys())
    return {k: v for k, v in timeperiods.items() if k not in builtin_keys}


class TimeperiodSelection(DropdownChoice):
    def __init__(self, **kwargs):
        kwargs.setdefault("no_preselect", True)
        kwargs.setdefault("no_preselect_title", _("Select a timeperiod"))
        DropdownChoice.__init__(self, choices=self._get_choices, **kwargs)

    def _get_choices(self):
        timeperiods = load_timeperiods()
        elements = [(name, "%s - %s" % (name, tp["alias"])) for (name, tp) in timeperiods.items()]

        always = ("24X7", _("Always"))
        if always[0] not in dict(elements):
            elements.insert(0, always)

        return sorted(elements, key=lambda x: x[1].lower())


def find_usages_of_timeperiod(time_period_name: str) -> list[TimeperiodUsage]:
    """Find all usages of a timeperiod

    Possible usages:
     - 1. rules: service/host-notification/check-period
     - 2. user accounts (notification period)
     - 3. excluded by other time periods
     - 4. time period condition in notification and alerting rules
     - 5. bulk operation in notification rules
     - 6. time period condition in EC rules
     - 7. rules: time specific parameters
    """
    used_in: list[TimeperiodUsage] = []
    used_in += _find_usages_in_host_and_service_rules(time_period_name)
    used_in += _find_usages_in_users(time_period_name)
    used_in += _find_usages_in_other_timeperiods(time_period_name)
    used_in += _find_usages_in_notification_rules(time_period_name)
    used_in += _find_usages_in_alert_handler_rules(time_period_name)
    used_in += _find_usages_in_ec_rules(time_period_name)
    used_in += _find_usages_in_time_specific_parameters(time_period_name)
    return used_in


def _find_usages_in_host_and_service_rules(time_period_name: str) -> list[TimeperiodUsage]:
    used_in: list[TimeperiodUsage] = []
    rulesets = watolib.AllRulesets()
    for varname, ruleset in rulesets.get_rulesets().items():
        if not isinstance(ruleset.valuespec(), TimeperiodSelection):
            continue

        for _folder, _rulenr, rule in ruleset.get_rules():
            if rule.value == time_period_name:
                used_in.append(
                    (
                        "{}: {}".format(_("Ruleset"), ruleset.title()),
                        folder_preserving_link([("mode", "edit_ruleset"), ("varname", varname)]),
                    )
                )
                break
    return used_in


def _find_usages_in_users(time_period_name: str) -> list[TimeperiodUsage]:
    used_in: list[TimeperiodUsage] = []
    for userid, user in userdb.load_users().items():
        tp = user.get("notification_period")
        if tp == time_period_name:
            used_in.append(
                (
                    "{}: {}".format(_("User"), userid),
                    folder_preserving_link([("mode", "edit_user"), ("edit", userid)]),
                )
            )

        for index, rule in enumerate(user.get("notification_rules", [])):
            used_in += _find_usages_in_notification_rule(
                time_period_name, index, rule, user_id=userid
            )
    return used_in


def _find_usages_in_other_timeperiods(time_period_name: str) -> list[TimeperiodUsage]:
    used_in: list[TimeperiodUsage] = []
    for tpn, tp in load_timeperiods().items():
        if time_period_name in tp.get("exclude", []):
            used_in.append(
                (
                    "%s: %s (%s)"
                    % (_("Time period"), timeperiod_spec_alias(tp, tpn), _("excluded")),
                    folder_preserving_link([("mode", "edit_timeperiod"), ("edit", tpn)]),
                )
            )
    return used_in


def _find_usages_in_notification_rules(time_period_name: str) -> list[TimeperiodUsage]:
    used_in: list[TimeperiodUsage] = []
    for index, rule in enumerate(load_notification_rules()):
        used_in += _find_usages_in_notification_rule(time_period_name, index, rule)
    return used_in


def _find_usages_in_notification_rule(
    time_period_name: str, index: int, rule: EventRule, user_id=None
) -> list[TimeperiodUsage]:
    def _used_in_tp_condition(rule, time_period_name):
        return rule.get("match_timeperiod") == time_period_name

    def _used_in_bulking(rule, time_period_name):
        bulk = rule.get("bulk")
        if isinstance(bulk, tuple):
            method, params = bulk
            return method == "timeperiod" and params["timeperiod"] == time_period_name
        return False

    used_in: list[TimeperiodUsage] = []
    if _used_in_tp_condition(rule, time_period_name) or _used_in_bulking(rule, time_period_name):
        url = folder_preserving_link(
            [
                ("mode", "notification_rule"),
                ("edit", index),
                ("user", user_id),
            ]
        )
        if user_id:
            title = _("Notification rule of user '%s'") % user_id
        else:
            title = _("Notification rule")

        used_in.append((title, url))
    return used_in


def _find_usages_in_alert_handler_rules(time_period_name: str) -> list[TimeperiodUsage]:
    used_in: list[TimeperiodUsage] = []
    if cmk_version.edition() is cmk_version.Edition.CRE or alert_handling is None:
        return used_in
    for index, rule in enumerate(alert_handling.load_alert_handler_rules()):
        if rule.get("match_timeperiod") == time_period_name:
            url = folder_preserving_link(
                [
                    ("mode", "alert_handler_rule"),
                    ("edit", index),
                ]
            )
            used_in.append((_("Alert handler rule"), url))
    return used_in


def _find_usages_in_ec_rules(time_period_name: str) -> list[TimeperiodUsage]:
    used_in: list[TimeperiodUsage] = []
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


def _find_usages_in_time_specific_parameters(time_period_name: str) -> list[TimeperiodUsage]:
    used_in: list[TimeperiodUsage] = []
    rulesets = watolib.AllRulesets()
    for ruleset in rulesets.get_rulesets().values():
        vs = ruleset.valuespec()
        if not isinstance(vs, watolib.rulespecs.TimeperiodValuespec):
            continue
        for rule_folder, rule_index, rule in ruleset.get_rules():
            if not vs.is_active(rule.value):
                continue
            for index, (rule_tp_name, _value) in enumerate(rule.value["tp_values"]):
                if rule_tp_name != time_period_name:
                    continue
                edit_url = folder_preserving_link(
                    [
                        ("mode", "edit_rule"),
                        ("back_mode", "timeperiods"),
                        ("varname", ruleset.name),
                        ("rulenr", rule_index),
                        ("rule_folder", rule_folder.path()),
                    ]
                )
                used_in.append((_("Time specific check parameter #%d") % (index + 1), edit_url))
    return used_in
