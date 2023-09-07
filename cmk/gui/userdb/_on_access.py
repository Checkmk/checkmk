#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from datetime import datetime

from cmk.utils.user import UserId

from cmk.gui.config import active_config
from cmk.gui.exceptions import MKAuthException

from .session import is_valid_user_session, load_session_infos
from .store import convert_idle_timeout, load_custom_attr


def on_access(username: UserId, session_id: str, now: datetime) -> None:
    """

    Raises:
        - MKAuthException: when the session given by session_id is not valid
        - MKAuthException: when the user has been idle for too long

    """
    session_infos = load_session_infos(username)
    if not is_valid_user_session(username, session_infos, session_id):
        raise MKAuthException("Invalid user session")

    # Check whether there is an idle timeout configured, delete cookie and
    # require the user to renew the log when the timeout exceeded.
    session_info = session_infos[session_id]
    _check_login_timeout(
        username,
        now.timestamp() - session_info.started_at,
        now.timestamp() - session_info.last_activity,
    )


def _check_login_timeout(username: UserId, session_duration: float, idle_time: float) -> None:
    _handle_max_duration(username, session_duration)
    _handle_idle_timeout(username, idle_time)


def _handle_max_duration(username: UserId, session_duration: float) -> None:
    if (
        max_duration := active_config.session_mgmt.get("max_duration", {}).get("enforce_reauth")
    ) and session_duration > max_duration:
        raise MKAuthException(
            f"{username} login timed out (Maximum session duration of {max_duration / 60} minutes exceeded)"
        )


def _handle_idle_timeout(username: UserId, idle_time: float) -> None:
    idle_timeout = load_custom_attr(
        user_id=username, key="idle_timeout", parser=convert_idle_timeout
    )
    if idle_timeout is None:
        idle_timeout = active_config.session_mgmt.get("user_idle_timeout")
    if idle_timeout is not None and idle_timeout is not False and idle_time > idle_timeout:
        raise MKAuthException(
            f"{username} login timed out (Maximum inactivity of {idle_timeout / 60} minutes exceeded)"
        )
