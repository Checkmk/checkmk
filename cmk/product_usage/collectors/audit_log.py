#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import ast
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

from cmk.product_usage.collectors.user_store import is_automation_user, load_users
from cmk.product_usage.schema import AuditLog, AuditLogActorClass

# The audit log writes this user ID for pseudo users and for actions without a user.
_NO_USER = "-"


def collect(
    var_dir: Path,
    default_config_dir: Path,
    *,
    platform_user_ids: frozenset[str],
) -> AuditLog:
    users = frozenset(load_users(default_config_dir))
    automation_users = frozenset(u for u in users if is_automation_user(var_dir / "web" / u))
    interactive, automation, platform = _Tally(), _Tally(), _Tally()
    for user_id, time in _read_entries(var_dir / "wato/log"):
        if user_id == _NO_USER or user_id in platform_user_ids:
            platform.add(time)
        elif user_id in automation_users:
            automation.add(time)
        # A deleted user is interactive if its ID is an email address, like a Cognito user's ID.
        elif user_id in users or "@" in user_id:
            interactive.add(time)
        else:
            automation.add(time)
    return AuditLog(
        interactive=interactive.actor_class(),
        automation=automation.actor_class(),
        platform=platform.actor_class(),
    )


@dataclass
class _Tally:
    entries: int = 0
    last_entry_at: int | None = None

    def add(self, time: int) -> None:
        self.entries += 1
        self.last_entry_at = time if self.last_entry_at is None else max(self.last_entry_at, time)

    def actor_class(self) -> AuditLogActorClass:
        return AuditLogActorClass(entries=self.entries, last_entry_at=self.last_entry_at)


def _read_entries(log_dir: Path) -> Iterator[tuple[str, int]]:
    """Yield the user ID and the time of each entry, in the current and the rotated audit logs

    Malformed lines are skipped.
    """
    for path in log_dir.glob("wato_audit.log*"):
        # A byte that is not valid UTF-8 then breaks only its own line, not the whole file
        with path.open(encoding="utf-8", errors="replace") as f:
            for line in f:
                if (entry := _parse(line)) is not None:
                    yield entry


def _parse(line: str) -> tuple[str, int] | None:
    try:
        raw = ast.literal_eval(line)
    except SyntaxError, ValueError, TypeError, RecursionError:
        return None
    match raw:
        case {"user_id": str(user_id), "time": int(time)}:
            return user_id, time
        case _:
            return None
