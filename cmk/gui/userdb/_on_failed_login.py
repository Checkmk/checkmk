#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from datetime import datetime

from cmk.ccc.user import UserId

from cmk.gui.config import active_config
from cmk.gui.http import request
from cmk.gui.log import logger as gui_logger
from cmk.gui.type_defs import UserSpec
from cmk.gui.utils import roles

from .store import load_users, save_users

auth_logger = gui_logger.getChild("auth")


def on_failed_login(username: UserId, now: datetime) -> None:
    users = load_users(lock=True)

    if (user := users.get(username)) and not roles.is_automation_user(username):
        _increment_failed_logins_and_lock(user)
        save_users(users, now)

    if active_config.log_logon_failures:
        if user:
            existing = "Yes"
            log_msg_until_locked = str(
                bool(active_config.lock_on_logon_failures) - user["num_failed_logins"]
            )
            if not user["locked"]:
                log_msg_locked = "No"
            elif log_msg_until_locked == "0":
                log_msg_locked = "Yes (now)"
            else:
                log_msg_locked = "Yes"
        else:
            existing = "No"
            log_msg_until_locked = "N/A"
            log_msg_locked = "N/A"
        auth_logger.warning(
            "Login failed for username: %s (existing: %s, locked: %s, failed logins until locked: %s), client: %s",
            username,
            existing,
            log_msg_locked,
            log_msg_until_locked,
            request.remote_ip,
        )


def _increment_failed_logins_and_lock(user: UserSpec) -> None:
    """Increment the number of failed logins for the user and lock the user if necessary."""
    user["num_failed_logins"] = user.get("num_failed_logins", 0) + 1

    if (
        active_config.lock_on_logon_failures
        and user["num_failed_logins"] >= active_config.lock_on_logon_failures
    ):
        user["locked"] = True
