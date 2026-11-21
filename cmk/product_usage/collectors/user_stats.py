#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Count the users of the site

Besides the user store (see user_store), this reads
etc/check_mk/multisite.d/wato/user_connections.mk for the type of each connection.

Only counts leave this module. Role names of custom roles and connection IDs are not part of the
result.
"""

from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import NamedTuple

from cmk.ccc.store import load_from_mk_file
from cmk.product_usage.collectors.user_store import StoredUser
from cmk.product_usage.schema import ActiveUsers, UserGroupData, UsersData

# Mirrors cmk.gui.config.builtin_role_ids
_BUILTIN_ROLE_IDS = frozenset({"user", "admin", "guest", "agent_registration", "no_permissions"})

# Connections that are not stored in user_connections.mk, see cmk.gui.userdb.builtin_connections
_BUILTIN_CONNECTION_TYPES: Mapping[str, str] = {
    "htpasswd": "htpasswd",
    "cognito": "oauth2",
}

_DAY = 86400


def collect(users: Iterable[StoredUser], default_config_dir: Path, now: int) -> UsersData:
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
    for user in users:
        info = _UserInfo(
            roles=_roles(user.attributes),
            connector_type=connection_types.get(
                str(user.attributes.get("connector", "htpasswd")), "unknown"
            ),
            last_seen=user.last_seen,
        )
        (automation if user.is_automation else humans).append(info)

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
