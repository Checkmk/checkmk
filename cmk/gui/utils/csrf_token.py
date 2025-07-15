#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from dataclasses import dataclass

from flask import session

from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.user import UserId

from cmk.utils.log.security_event import log_security_event, SecurityEvent

from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.logged_in import LoggedInNobody


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


def check_csrf_token(token: str | None = None) -> None:
    # We have to assert the attributes, due to importing flask.session because of
    # circular imports.
    assert hasattr(session, "user")  # mypy
    if isinstance(session.user, LoggedInNobody):
        return

    csrf_token = token or request.get_str_input("_csrf_token")
    if csrf_token is None:
        csrf_token = request.get_request().get("_csrf_token")

    if csrf_token is None:
        log_security_event(
            CSRFTokenMissingEvent(
                username=session.user.id,
                remote_ip=request.remote_ip,
            )
        )
        raise MKGeneralException(_("No CSRF token received"))

    assert hasattr(session, "session_info")  # mypy
    if csrf_token != session.session_info.csrf_token:
        log_security_event(
            CSRFTokenValidationFailureEvent(
                username=session.user.id,
                remote_ip=request.remote_ip,
            )
        )
        raise MKGeneralException(
            _("Invalid CSRF token (%r) for session (%r)")
            % (csrf_token, session.session_info.session_id)
        )
