#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Lightweight user-context utilities.

These context managers swap `flask.session.user` for the duration of a block.
They are split out of :mod:`cmk.gui.session` so that callers like
``cmk.gui.watolib`` can use them without pulling in the heavy login/userdb
machinery that lives in the rest of `session.py`.
"""

from __future__ import annotations

import contextlib
from collections.abc import Container, Iterator
from contextlib import AbstractContextManager as ContextManager

import flask

from cmk.ccc.user import UserId
from cmk.gui import config
from cmk.gui.logged_in import (
    LoggedInSuperUser,
    LoggedInUser,
    UserDefaultConfig,
)
from cmk.gui.utils.roles import UserPermissions


def _user_defaults() -> UserDefaultConfig:
    return UserDefaultConfig(
        users=config.active_config.multisite_users,
        default_language=config.active_config.default_language,
        default_show_mode=config.active_config.show_mode,
    )


@contextlib.contextmanager
def _UserContext(user_obj: LoggedInUser) -> Iterator[None]:
    """Managing authenticated user context

    After the user has been authenticated, initialize the global user object."""
    old_user: LoggedInUser = flask.session.user  # type: ignore[attr-defined]
    flask.session.user = user_obj  # type: ignore[attr-defined]
    try:
        yield
    finally:
        flask.session.user = old_user  # type: ignore[attr-defined]


def UserContext(
    user_id: UserId,
    user_permissions: UserPermissions,
    *,
    explicit_permissions: Container[str] = frozenset(),
) -> ContextManager[None]:
    """Execute a block of code as another user

    After the block exits, the previous user will be replaced again.
    """
    return _UserContext(
        LoggedInUser(
            user_id,
            user_permissions,
            defaults=_user_defaults(),
            explicitly_given_permissions=explicit_permissions,
        )
    )


def SuperUserContext() -> ContextManager[None]:
    """Execute a block code as the superuser

    After the block exits, the previous user will be replaced again.
    """
    return _UserContext(LoggedInSuperUser())


def get_session_csrf_token() -> str | None:
    """Return the current request's CSRF token, or None if no session is set up.

    Provided here so callers that only need the CSRF token don't have to import
    the typed `session` proxy from :mod:`cmk.gui.session` (which is in the heavy
    :auth target).
    """
    s = flask.session
    if s and hasattr(s, "session_info"):
        token: str = s.session_info.csrf_token
        return token
    return None
