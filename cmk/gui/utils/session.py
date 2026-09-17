#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""The session as a page handler sees it.

``cmk.gui.session`` owns the implementation, but it sits in //cmk/gui:auth,
which most of the GUI is below. The protocol and the request-local object are
therefore declared here, next to the code reading them.
"""

from typing import cast, Protocol

import flask

from cmk.ccc.user import UserId


class SessionUserProtocol(Protocol):
    """The part of the logged-in user a session hands to a page handler."""

    @property
    def id(self) -> UserId | None: ...

    @property
    def is_anonymous(self) -> bool: ...


class SessionInfoProtocol(Protocol):
    """The part of the session info a page handler reads."""

    @property
    def csrf_token(self) -> str: ...


class SessionProtocol(Protocol):
    """The part of the session a page handler is given.

    Kept to what callers actually read so that a page need not know the whole
    session implementation, and free of cmk.gui types so the readers can move
    out of it.
    """

    @property
    def user(self) -> SessionUserProtocol: ...

    @property
    def session_info(self) -> SessionInfoProtocol: ...


# The same request-local object as cmk.gui.session.session, seen through the
# narrower protocol.
session: SessionProtocol = cast(SessionProtocol, flask.session)
