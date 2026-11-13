#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Count the users of the site

The GUI owns the user database, but this package must not import it. The few files read here are
therefore read directly:

- etc/check_mk/multisite.d/wato/users.mk: roles and connection ID of each user
- etc/check_mk/multisite.d/wato/user_connections.mk: the type of each connection
- var/check_mk/web/<user>/automation_user.mk, automation.secret: automation user flag
- var/check_mk/web/<user>/session_info.mk: last activity of the GUI sessions
- var/check_mk/web/<user>/last_login.mk: last request authenticated by a header (REST API,
  basic auth, ...). This is written for automation users on every request.

Only counts leave this module. User IDs, role names of custom roles and connection IDs are not
part of the result.
"""

import ast
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import NamedTuple

from cmk.ccc.store import load_from_mk_file
from cmk.product_usage.collectors.user_store import load_users
from cmk.product_usage.schema import ActiveUsers, UserGroupData, UsersData

# Mirrors cmk.gui.config.builtin_role_ids
_BUILTIN_ROLE_IDS = frozenset({"user", "admin", "guest", "agent_registration", "no_permissions"})

# Connections that are not stored in user_connections.mk, see cmk.gui.userdb.builtin_connections
_BUILTIN_CONNECTION_TYPES: Mapping[str, str] = {
    "htpasswd": "htpasswd",
    "cognito": "oauth2",
}

_DAY = 86400


def collect(default_config_dir: Path, profile_dir: Path, now: int) -> UsersData:
    users = load_users(default_config_dir)
    connections: list[Mapping[str, object]] = load_from_mk_file(
        default_config_dir / "multisite.d" / "wato" / "user_connections.mk",
        key="user_connections",
        default=[],
        lock=False,
    )
    connection_types = {
        **_BUILTIN_CONNECTION_TYPES,
        **{str(c["id"]): str(c["type"]) for c in connections},
    }

    humans: list[_UserInfo] = []
    automation: list[_UserInfo] = []
    for user_id, user in users.items():
        user_dir = profile_dir / user_id
        info = _UserInfo(
            roles=_roles(user),
            connector_type=connection_types.get(str(user.get("connector", "htpasswd")), "unknown"),
            last_seen=_last_seen(user_dir),
        )
        (automation if _is_automation_user(user_dir) else humans).append(info)

    return UsersData(
        humans=_group_data(humans, now),
        automation=_group_data(automation, now),
    )


class _UserInfo(NamedTuple):
    roles: Sequence[str]
    connector_type: str
    last_seen: int


def _roles(user: Mapping[str, object]) -> list[str]:
    roles = user.get("roles", [])
    assert isinstance(roles, list)
    # A user having several custom roles is counted once for "custom"
    return sorted({role if role in _BUILTIN_ROLE_IDS else "custom" for role in roles})


def _group_data(users: list[_UserInfo], now: int) -> UserGroupData:
    return UserGroupData(
        total=len(users),
        by_role=dict(Counter(role for user in users for role in user.roles)),
        by_connector_type=dict(Counter(user.connector_type for user in users)),
        active=ActiveUsers(
            {
                "24h": _count_active(users, now - _DAY),
                "7d": _count_active(users, now - 7 * _DAY),
                "30d": _count_active(users, now - 30 * _DAY),
            }
        ),
    )


def _count_active(users: Iterable[_UserInfo], since: int) -> int:
    return sum(1 for user in users if user.last_seen >= since)


def _is_automation_user(user_dir: Path) -> bool:
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
    try:
        content = path.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return None
    return ast.literal_eval(content) if content else None
