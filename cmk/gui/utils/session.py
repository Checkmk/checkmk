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

from cmk.gui.logged_in import LoggedInUser
from cmk.gui.type_defs import SessionInfo


class SessionProtocol(Protocol):
    """The part of the session a page handler is given.

    Kept to what callers actually read so that a page need not know the whole
    session implementation.
    """

    @property
    def user(self) -> LoggedInUser: ...

    @property
    def session_info(self) -> SessionInfo: ...


# The same request-local object as cmk.gui.session.session, seen through the
# narrower protocol.
session: SessionProtocol = cast(SessionProtocol, flask.session)
