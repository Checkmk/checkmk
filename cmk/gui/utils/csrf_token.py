#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Callable
from dataclasses import dataclass

from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.user import UserId
from cmk.gui.utils.session import SessionProtocol
from cmk.utils.security_event import log_security_event, SecurityEvent
from cmk.web.context import RequestProtocol


@dataclass
class CSRFTokenValidationFailureEvent(SecurityEvent):
    """Indicates failed CSRF token validation"""

    def __init__(self, *, username: UserId | None, remote_ip: str | None) -> None:
        super().__init__(
            "CSRF token validation failed",
            {
                "user": str(username or "Unknown user"),
                "remote_ip": remote_ip,
            },
            SecurityEvent.Domain.application_errors,
        )


@dataclass
class CSRFTokenMissingEvent(SecurityEvent):
    """Indicates missing CSRF token"""

    def __init__(self, *, username: UserId | None, remote_ip: str | None) -> None:
        super().__init__(
            "CSRF token missing",
            {
                "user": str(username or "Unknown user"),
                "remote_ip": remote_ip,
            },
            SecurityEvent.Domain.application_errors,
        )


def check_csrf_token(
    session: SessionProtocol,
    request: RequestProtocol,
    *,
    i18n: Callable[[str], str],
    token: str | None = None,
) -> None:
    if session.user.is_anonymous:
        return

    csrf_token = token or request.get_str_input("_csrf_token")
    if csrf_token is None:
        # The token may also arrive in the request body rather than as a variable.
        from_body = request.get_request().get("_csrf_token")
        csrf_token = from_body if isinstance(from_body, str) else None

    if csrf_token is None:
        log_security_event(
            CSRFTokenMissingEvent(
                username=session.user.id,
                remote_ip=request.remote_ip,
            )
        )
        raise MKGeneralException(i18n("No CSRF token received"))

    if csrf_token != session.session_info.csrf_token:
        log_security_event(
            CSRFTokenValidationFailureEvent(
                username=session.user.id,
                remote_ip=request.remote_ip,
            )
        )
        raise MKGeneralException(
            i18n("Invalid CSRF token (%(csrf_token)r)") % {"csrf_token": csrf_token}
        )
