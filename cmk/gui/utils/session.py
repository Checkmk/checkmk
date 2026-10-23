#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""The request-local session, seen through the protocol a page handler is given.

``cmk.gui.session`` owns the implementation, but it sits in //cmk/gui:auth,
which most of the GUI is below, so the narrow view is offered from here.
"""

from typing import cast

import flask

from cmk.web.context import SessionProtocol as SessionProtocol

# The same request-local object as cmk.gui.session.session.
session: SessionProtocol = cast(SessionProtocol, flask.session)
