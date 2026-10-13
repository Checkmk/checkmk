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
from ._login_timeout import LoginTimeoutStore
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
    time_based_lock_out_enabled: bool,
    log_logon_failures: bool,
    pprint_value: bool,
) -> None:
    existing: bool | None = None

    if time_based_lock_out_enabled:
        is_automation_user = roles.is_automation_user(username)
        store = LoginTimeoutStore()
        if not is_automation_user:
            store.record_failed_login(username, request.remote_ip, now)

        if log_logon_failures:
            status = store.timeout_status(
                username, request.remote_ip, now, cleanup=is_automation_user
            )
            existing = user_exists(username)
            if status.ip_timed_out or (existing and status.user_timed_out):
                _log_failed_login(
                    username,
                    existing,
                    {
                        "ip timed out": "Yes" if status.ip_timed_out else "No",
                        "user timed out": "Yes" if existing and status.user_timed_out else "No",
                    },
                )

    if not lock_on_logon_failures:
        if log_logon_failures:
            _log_failed_login(
                username,
                existing if existing is not None else user_exists(username),
                {"locked": "N/A", "failed logins until locked": "N/A"},
            )
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
            _log_failed_login(
                username,
                True,
                {"locked": log_msg_locked, "failed logins until locked": log_msg_until_locked},
            )
        else:
            _log_failed_login(
                username, False, {"locked": "N/A", "failed logins until locked": "N/A"}
            )


def _log_failed_login(username: UserId, existing: bool, details: dict[str, str]) -> None:
    auth_logger.warning(
        "Login failed for username: %(username)s (existing: %(existing)s, %(details)s), client: %(client_ip)s",
        {
            "username": username,
            "existing": "Yes" if existing else "No",
            "details": ", ".join(f"{k}: {v}" for k, v in details.items()),
            "client_ip": request.remote_ip,
        },
    )


def _increment_failed_logins_and_lock(user: UserSpec, lock_on_logon_failures: int | None) -> None:
    """Increment the number of failed logins for the user and lock the user if necessary."""
    user["num_failed_logins"] = user.get("num_failed_logins", 0) + 1

    if lock_on_logon_failures and user["num_failed_logins"] >= lock_on_logon_failures:
        user["locked"] = True
