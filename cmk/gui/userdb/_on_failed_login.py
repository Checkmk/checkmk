#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from datetime import datetime

from cmk.ccc.user import UserId
from cmk.gui.http import request
from cmk.gui.log import logger as gui_logger
from cmk.gui.type_defs import UserSpec
from cmk.gui.user_connection_config_types import UserConnectionConfig
from cmk.gui.utils import roles

from ._check_credentials import user_exists
from ._user_attribute import UserAttribute
from .store import load_users, save_users

auth_logger = gui_logger.getChild("auth")


def on_failed_login(
    username: UserId,
    user_attributes: Sequence[tuple[str, UserAttribute]],
    user_connections: Sequence[UserConnectionConfig],
    *,
    now: datetime,
    lock_on_logon_failures: int | None,
    log_logon_failures: bool,
    pprint_value: bool,
) -> None:
    if not lock_on_logon_failures:
        if log_logon_failures:
            _log_failed_login(username, "Yes" if user_exists(username) else "No", "N/A", "N/A")
        return

    all_users = load_users(lock=True)

    if (user := all_users.get(username)) and not roles.is_automation_user(username):
        _increment_failed_logins_and_lock(user, lock_on_logon_failures)
        save_users(
            all_users,
            user_attributes,
            user_connections,
            now,
            pprint_value=pprint_value,
            call_users_saved_hook=True,
            changed_users=[username],
        )

    if log_logon_failures:
        if user:
            log_msg_until_locked = str(bool(lock_on_logon_failures) - user["num_failed_logins"])
            if not user["locked"]:
                log_msg_locked = "No"
            elif log_msg_until_locked == "0":
                log_msg_locked = "Yes (now)"
            else:
                log_msg_locked = "Yes"
            _log_failed_login(username, "Yes", log_msg_locked, log_msg_until_locked)
        else:
            _log_failed_login(username, "No", "N/A", "N/A")


def _log_failed_login(
    username: UserId, existing: str, locked: str, failed_logins_until_locked: str
) -> None:
    auth_logger.warning(
        "Login failed for username: %(username)s (existing: %(existing)s, locked: %(locked)s, "
        "failed logins until locked: %(until_locked)s), client: %(client_ip)s",
        {
            "username": username,
            "existing": existing,
            "locked": locked,
            "until_locked": failed_logins_until_locked,
            "client_ip": request.remote_ip,
        },
    )


def _increment_failed_logins_and_lock(user: UserSpec, lock_on_logon_failures: int | None) -> None:
    """Increment the number of failed logins for the user and lock the user if necessary."""
    user["num_failed_logins"] = user.get("num_failed_logins", 0) + 1

    if lock_on_logon_failures and user["num_failed_logins"] >= lock_on_logon_failures:
        user["locked"] = True
