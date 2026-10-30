#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Helpers shared by the tests of the internal gui_session endpoints and their fixtures."""

import time
from typing import Protocol

from cmk.ccc.user import UserId
from cmk.gui.type_defs import SessionInfo, SessionState
from cmk.gui.userdb.session import auth_cookie_value, create_session_id, save_session_infos
from cmk.utils.local_secrets import SiteInternalSecret


class SessionCookieFactory(Protocol):
    def __call__(
        self,
        user_id: UserId,
        *,
        state: SessionState = ...,
        age_seconds: int = ...,
        idle_seconds: int = ...,
    ) -> tuple[str, str]: ...


def internal_token_header() -> dict[str, str]:
    """The Authorization header a site component sends."""
    return {"Authorization": f"InternalToken {SiteInternalSecret().secret.b64_str}"}


def make_session_cookie(
    user_id: UserId,
    *,
    state: SessionState = "logged_in",
    age_seconds: int = 0,
    idle_seconds: int = 0,
) -> tuple[str, str]:
    """Store a GUI session for a user and return its id and cookie value.

    age_seconds is how long ago the session started, idle_seconds how long
    ago it was last used. A session is never used before it starts.
    """
    session_id = create_session_id()
    now = int(time.time())
    save_session_infos(
        user_id,
        {
            session_id: SessionInfo(
                session_id=session_id,
                started_at=now - max(age_seconds, idle_seconds),
                last_activity=now - idle_seconds,
                auth_type="cookie",
                session_state=state,
            )
        },
    )
    return session_id, auth_cookie_value(user_id, session_id)
