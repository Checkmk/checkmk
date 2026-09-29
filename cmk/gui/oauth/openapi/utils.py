#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import http.client
from datetime import datetime
from typing import Literal

from cmk.ccc.user import UserId
from cmk.gui.config import active_config
from cmk.gui.logged_in import LoggedInSuperUser
from cmk.gui.openapi.framework import ApiContext
from cmk.gui.openapi.utils import EXT, ProblemException
from cmk.gui.utils.security_log_events import GUISessionRejectedEvent
from cmk.utils.security_event import log_security_event

from .session_check import verify_gui_session


def require_site_internal_caller(api_context: ApiContext) -> None:
    """Refuse every caller except one holding the site-internal secret."""
    if not isinstance(api_context.user, LoggedInSuperUser):
        raise ProblemException(
            status=http.client.UNAUTHORIZED,
            title=http.client.responses[http.client.UNAUTHORIZED],
            detail="This endpoint is reserved for Checkmk.",
        )


def live_session_user(
    api_context: ApiContext, session_cookie: str, *, endpoint: Literal["identify", "delegate"]
) -> UserId:
    """The user behind the cookie, or a 400 that says nothing about why.

    Why the session was refused goes to the security log instead.
    """
    session_mgmt = active_config.session_mgmt
    verdict = verify_gui_session(
        session_cookie,
        max_duration=session_mgmt.get("max_duration", {}).get("enforce_reauth"),
        default_idle_timeout=session_mgmt.get("user_idle_timeout"),
        user_permissions=api_context.config.user_permissions(),
        now=datetime.now(),
    )
    if not verdict.is_ok():
        rejected = verdict.error
        log_security_event(
            GUISessionRejectedEvent(
                reason=rejected.reason, user_id=rejected.user_id, endpoint=endpoint
            )
        )
        # The OAuth error code tells the caller this is a verdict on the
        # session. Other 400 answers, such as a malformed body, carry none.
        raise ProblemException(
            status=http.client.BAD_REQUEST,
            title="Invalid session",
            detail="The session cookie does not belong to a live session.",
            ext=EXT({"error": "invalid_grant"}),
        )
    return verdict.ok
