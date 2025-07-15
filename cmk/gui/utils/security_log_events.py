#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from dataclasses import dataclass
from enum import Enum
from typing import Literal

from cmk.ccc.user import UserId

from cmk.utils.log.security_event import SecurityEvent

from cmk.gui.type_defs import AuthType


class TwoFactorEventType(Enum):
    totp_add = "Authenticator application key added"
    totp_remove = "Authenticator application key revoked"
    webauthn_add_ = "Webauthn key added"
    webauthn_remove = "Webauthn key revoked"
    backup_add = "New backup codes generated, previous revoked"
    backup_remove = "All backup codes revoked"
    backup_used = "Backup code used for authentication"


@dataclass
class AuthenticationFailureEvent(SecurityEvent):
    """Indicates a failed authentication attempt"""

    def __init__(
        self,
        *,
        user_error: str,
        auth_method: AuthType,
        username: UserId | None,
        remote_ip: str | None,
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

    def __init__(
        self, *, auth_method: AuthType, username: UserId | None, remote_ip: str | None
    ) -> None:
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
class TwoFAFailureEvent(SecurityEvent):
    """Indicates a failed 2FA attempt"""

    def __init__(
        self, *, user_error: str, two_fa_method: str, username: UserId | None, remote_ip: str | None
    ) -> None:
        super().__init__(
            "2FA authentication failed",
            {
                "user_error": user_error,
                "method": two_fa_method,
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
        connector: str | None = None,
        connection_id: str | None = None,
    ) -> None:
        details = {
            "affected_user": str(affected_user),
            "acting_user": str(acting_user or "Unknown user"),
        }
        if connector is not None:
            details["connector"] = connector
            details["connection_id"] = str(connection_id or "Unknown connection")

        super().__init__(
            event,
            details,
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
