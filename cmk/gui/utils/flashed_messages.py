#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Flashing messages to the next request.

Inspired by generic logic flask flashed messages, but implemented in a simpler way.
Flask uses a generic session cookie store which we don't want to implement here for
simplicity. In case we have such a generic thing, it will be easy to switch to it.
"""

from typing import List, Union

from cmk.gui.ctx_stack import request_stack
from cmk.gui.userdb import session
from cmk.gui.utils.escaping import escape_text
from cmk.gui.utils.html import HTML


def flash(message: Union[str, HTML]) -> None:
    """To handle both, HTML and str, correctly we need to a) escape the given str for HTML and
    cast the HTML objects to str. Before handing back the messages to the consumer, all need to
    converted back to HTML (see get_flashed_messages())
    """
    if isinstance(message, str):
        normalized = escape_text(message)
    else:
        normalized = str(message)
    session.session_info.flashes.append(normalized)


def get_flashed_messages() -> List[HTML]:
    """Return the messages flashed from the previous request to this one

    Move the flashes from the session object to the current request once and
    cache them for the current request.
    """
    flashes = request_stack().top.flashes
    if flashes is None:
        if not hasattr(session, "session_info") or not session.session_info.flashes:
            request_stack().top.flashes = []
        else:
            request_stack().top.flashes = session.session_info.flashes
            session.session_info.flashes = []

    return [HTML(s) for s in request_stack().top.flashes]
