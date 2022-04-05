#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Module for managing the new rule based notifications"""

from typing import Dict, List

import cmk.utils.store as store
from cmk.utils.type_defs import EventRule, UserId

import cmk.gui.userdb as userdb
from cmk.gui.globals import config
from cmk.gui.watolib.utils import wato_root_dir


def load_notification_rules(lock: bool = False) -> List[EventRule]:
    filename = wato_root_dir() + "notifications.mk"
    notification_rules = store.load_from_mk_file(filename, "notification_rules", [], lock=lock)

    # Convert to new plugin configuration format
    for rule in notification_rules:
        if "notify_method" in rule:
            method = rule["notify_method"]
            plugin = rule["notify_plugin"]
            del rule["notify_method"]
            rule["notify_plugin"] = (plugin, method)

    return notification_rules


def save_notification_rules(rules: list[EventRule]) -> None:
    store.mkdir(wato_root_dir())
    store.save_to_mk_file(
        wato_root_dir() + "notifications.mk",
        "notification_rules",
        rules,
        pprint_value=config.wato_pprint_config,
    )


def load_user_notification_rules() -> Dict[UserId, List[EventRule]]:
    rules = {}
    for user_id, user in userdb.load_users().items():
        user_rules = user.get("notification_rules")
        if user_rules:
            rules[user_id] = user_rules
    return rules
