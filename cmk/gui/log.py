#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from dataclasses import dataclass
from enum import Enum
from logging import FileHandler, Formatter, getLogger
from pathlib import Path
from typing import Literal

import cmk.utils.log
import cmk.utils.paths
from cmk.utils.log.security_event import SecurityEvent
from cmk.utils.user import UserId

logger = getLogger("cmk.web")


class TwoFactorEventType(Enum):
    totp_add = "Authenticator application key added"
    totp_remove = "Authenticator application key revoked"
    webauthn_add_ = "Webauthn key added"
    webauthn_remove = "Webauthn key revoked"
    backup_add = "New backup codes generated, previous revoked"
    backup_remove = "All backup codes revoked"
    backup_used = "Backup code used for authentication"


def init_logging() -> None:
    handler = FileHandler(Path(cmk.utils.paths.log_dir, "web.log"), encoding="UTF-8")
    handler.setFormatter(Formatter("%(asctime)s [%(levelno)s] [%(name)s %(process)d] %(message)s"))
    root = getLogger()
    del root.handlers[:]  # Remove all previously existing handlers
    root.addHandler(handler)


def set_log_levels(log_levels: dict[str, int]) -> None:
    for name, level in _augmented_log_levels(log_levels).items():
        getLogger(name).setLevel(level)


# To see log entries from libraries and non-GUI code, reuse cmk.web's level.
def _augmented_log_levels(log_levels: dict[str, int]) -> dict[str, int]:
    root_level = log_levels.get("cmk.web")
    all_levels = {} if root_level is None else {"": root_level, "cmk": root_level}
    all_levels.update(log_levels)
    return all_levels


@dataclass
class AuthenticationFailureEvent(SecurityEvent):
    """Indicates a failed authentication attempt"""

    def __init__(
        self, *, user_error: str, auth_method: str, username: UserId | None, remote_ip: str | None
    ) -> None:
        super().__init__(
            "authentication failed",
            {
                "user_error": user_error,  # Note: may be localized
                "method": auth_method,
                "user": str(username or "Unknown user"),
                "remote_ip": remote_ip,
            },
            SecurityEvent.Domain.auth,
        )


@dataclass
class AuthenticationSuccessEvent(SecurityEvent):
    """Indicates a successful authentication"""

    def __init__(self, *, auth_method: str, username: UserId | None, remote_ip: str | None) -> None:
        super().__init__(
            "authentication succeeded",
            {
                "method": auth_method,
                "user": str(username or "Unknown user"),
                "remote_ip": remote_ip,
            },
            SecurityEvent.Domain.auth,
        )


@dataclass
class UserManagementEvent(SecurityEvent):
    """Indicates a user creation, modification or deletion"""

    def __init__(
        self,
        *,
        event: Literal["user created", "user deleted", "user modified", "password changed"],
        affected_user: UserId,
        acting_user: UserId | None,
    ) -> None:
        super().__init__(
            event,
            {
                "affected_user": str(affected_user),
                "acting_user": str(acting_user or "Unknown user"),
            },
            SecurityEvent.Domain.user_management,
        )


@dataclass
class TwoFactorEvent(SecurityEvent):
    """Indicates a user has added, or removed two factor controls"""

    def __init__(
        self,
        *,
        event: TwoFactorEventType,
        username: UserId,
    ) -> None:
        super().__init__(
            event.value,
            {
                "user": str(username),
            },
            SecurityEvent.Domain.user_management,
        )
