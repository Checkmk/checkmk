#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Read the GUI's user store

The GUI owns the user database, but this package must not import it. The few files read here are
therefore read directly:

- etc/check_mk/multisite.d/wato/users.mk: the attributes of each user
- var/check_mk/web/<user>/automation_user.mk, automation.secret: automation user flag
- var/check_mk/web/<user>/session_info.mk: last activity of the GUI sessions
- var/check_mk/web/<user>/last_login.mk: last request authenticated by a header (REST API,
  basic auth, ...). This is written for automation users on every request.
"""

import ast
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import NamedTuple

from cmk.ccc import store


class StoredUser(NamedTuple):
    attributes: Mapping[str, object]
    is_automation: bool
    last_seen: int
    """Time of the most recent activity, 0 if the user was never active"""


def load_users(default_config_dir: Path) -> Mapping[str, Mapping[str, object]]:
    """The users in the GUI's user store, by user ID"""
    users: Mapping[str, Mapping[str, object]] = store.load_from_mk_file(
        default_config_dir / "multisite.d/wato/users.mk",
        key="multisite_users",
        default={},
        lock=False,
    )
    return users


def load_users_with_profiles(default_config_dir: Path, profile_dir: Path) -> Sequence[StoredUser]:
    """The users in the GUI's user store with the data of their profile directory

    The result carries no user IDs, so that they cannot end up in the collected data.
    """
    return [
        StoredUser(
            attributes=attributes,
            is_automation=is_automation_user(profile_dir / user_id),
            last_seen=_last_seen(profile_dir / user_id),
        )
        for user_id, attributes in load_users(default_config_dir).items()
    ]


def is_automation_user(user_dir: Path) -> bool:
    # Same check as cmk.gui.userdb.store: the automation_user.mk file was added with 2.4, before
    # that the automation secret was the only indicator.
    return (user_dir / "automation.secret").is_file() or _read_literal(
        user_dir / "automation_user.mk"
    ) is True


def _last_seen(user_dir: Path) -> int:
    """Most recent activity of the user, like cmk.gui.userdb.get_last_seen"""
    timestamps = [0]

    session_infos = _read_literal(user_dir / "session_info.mk")
    if isinstance(session_infos, dict):
        timestamps.extend(
            int(session["last_activity"])
            for session in session_infos.values()
            if isinstance(session, dict) and "last_activity" in session
        )

    last_login = _read_literal(user_dir / "last_login.mk")
    if isinstance(last_login, dict) and "timestamp" in last_login:
        timestamps.append(int(last_login["timestamp"]))

    return max(timestamps)


def _read_literal(path: Path) -> object:
    """The literal in the file, None if the file is missing, empty or unreadable

    A broken profile file of one user must not stop the counting of all users.
    """
    try:
        content = path.read_text(encoding="utf-8").strip()
        return ast.literal_eval(content) if content else None
    except (
        FileNotFoundError,
        UnicodeDecodeError,
        SyntaxError,
        ValueError,
        TypeError,
        MemoryError,
        RecursionError,
    ):
        return None
