#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.ccc.user import UserId

from cmk.utils.notify_types import EventRule

from cmk.gui.groups import GroupName
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.type_defs import GlobalSettings
from cmk.gui.utils.urls import makeuri_contextless

from .store import load_users


def find_usages_of_contact_group_in_users(
    name: GroupName, _settings: GlobalSettings
) -> list[tuple[str, str]]:
    """Is the contactgroup assigned to a user?"""
    used_in = []
    users = load_users()
    for userid, user_spec in sorted(users.items(), key=lambda x: x[1].get("alias", x[0])):
        cgs = user_spec.get("contactgroups", [])
        if name in cgs:
            used_in.append(
                (
                    "{}: {}".format(_("User"), user_spec.get("alias", userid)),
                    makeuri_contextless(
                        request, [("mode", "edit_user"), ("edit", userid)], filename="wato.py"
                    ),
                )
            )
    return used_in


def find_timeperiod_usage_in_users(time_period_name: str) -> list[tuple[str, str]]:
    used_in: list[tuple[str, str]] = []
    for userid, user in load_users().items():
        tp = user.get("notification_period")
        if tp == time_period_name:
            used_in.append(
                (
                    "{}: {}".format(_("User"), userid),
                    makeuri_contextless(
                        request, [("mode", "edit_user"), ("edit", userid)], filename="wato.py"
                    ),
                )
            )

        for index, rule in enumerate(user.get("notification_rules", [])):
            used_in += find_timeperiod_usage_in_notification_rule(
                time_period_name, index, rule, user_id=userid
            )
    return used_in


def find_timeperiod_usage_in_notification_rule(
    time_period_name: str, index: int, rule: EventRule, user_id: UserId | None = None
) -> list[tuple[str, str]]:
    def _used_in_tp_condition(rule, time_period_name):
        return rule.get("match_timeperiod") == time_period_name

    def _used_in_bulking(rule, time_period_name):
        bulk = rule.get("bulk")
        if isinstance(bulk, tuple):
            method, params = bulk
            return method == "timeperiod" and params["timeperiod"] == time_period_name
        return False

    used_in: list[tuple[str, str]] = []
    if _used_in_tp_condition(rule, time_period_name) or _used_in_bulking(rule, time_period_name):
        url = makeuri_contextless(
            request,
            [
                ("mode", "notification_rule"),
                ("edit", index),
                ("user", user_id),
            ],
            filename="wato.py",
        )
        if user_id:
            title = _("Notification rule of user '%s'") % user_id
        else:
            title = _("Notification rule")

        used_in.append((title, url))
    return used_in
