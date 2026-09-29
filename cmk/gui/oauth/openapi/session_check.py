#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime

from cmk.ccc.resulttype import Error, OK, Result
from cmk.ccc.user import UserId
from cmk.gui.auth import parse_and_check_cookie
from cmk.gui.exceptions import MKAuthException
from cmk.gui.permissions import permission_registry
from cmk.gui.userdb import convert_idle_timeout, load_custom_attr, load_session_infos, load_user
from cmk.gui.userdb.session import active_sessions
from cmk.gui.utils.roles import UserPermissions

_GUI_USE_PERMISSION = "general.use"


@dataclass(frozen=True, slots=True)
class SessionRejected:
    """Why the session was refused, for the security log, not sent to the caller"""

    reason: str
    # None until the cookie is verified, its user name is not to be trusted before.
    user_id: UserId | None = None


def verify_gui_session(
    cookie_value: str,
    *,
    max_duration: int | None,
    default_idle_timeout: int | None,
    user_permissions: UserPermissions,
    now: datetime,
) -> Result[UserId, SessionRejected]:
    """Returns the user behind a live GUI session, or why the session is not accepted."""
    # The cookie hash is compared with hmac.compare_digest on str, which
    # raises instead of failing for non-ASCII input.
    if not cookie_value.isascii():
        return Error(SessionRejected("cookie is not ASCII"))
    try:
        user_id, session_id, _cookie_hash = parse_and_check_cookie(cookie_value)
    except MKAuthException:
        return Error(SessionRejected("cookie does not verify"))

    info = active_sessions(load_session_infos(user_id), now).get(session_id)
    # Only a fully established session counts. The other states mean the
    # user is still in the login flow, for example waiting for a second factor.
    if info is None or info.session_state != "logged_in":
        return Error(SessionRejected("session is not logged in", user_id))

    if max_duration and now.timestamp() - info.started_at > max_duration:
        return Error(SessionRejected("session exceeded its maximum duration", user_id))

    idle_timeout = load_custom_attr(
        user_id=user_id, key="idle_timeout", parser=convert_idle_timeout
    )
    if idle_timeout is None:
        idle_timeout = default_idle_timeout
    if (
        idle_timeout is not None
        and idle_timeout is not False
        and int(now.timestamp()) - info.last_activity > idle_timeout
    ):
        return Error(SessionRejected("session exceeded its idle timeout", user_id))

    if load_user(user_id).get("locked", False):
        return Error(SessionRejected("user is locked", user_id))

    # Check if the user may use the GUI at all
    if not user_permissions.user_may(user_id, _GUI_USE_PERMISSION):
        return Error(SessionRejected("user may not use the GUI", user_id))

    return OK(user_id)


def held_permissions(
    user_id: UserId, names: Iterable[str], *, user_permissions: UserPermissions
) -> dict[str, bool]:
    """Whether the user holds each named permission. An unregistered name is never held."""
    # A role keeps a saved grant after its permission is gone, so check the registry too.
    return {
        name: name in permission_registry and user_permissions.user_may(user_id, name)
        for name in names
    }
