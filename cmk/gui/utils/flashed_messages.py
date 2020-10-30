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

from typing import List
from cmk.gui.globals import session, _request_ctx_stack


def flash(message: str) -> None:
    session.session_info.flashes.append(message)


def get_flashed_messages() -> List[str]:
    """Return the messages flashed from the previous request to this one

    Move the flashes from the session object to the current request once and
    cache them for the current request.
    """
    flashes = _request_ctx_stack.top.flashes
    if flashes is None:
        if not session.session_info.flashes:
            _request_ctx_stack.top.flashes = []
        else:
            _request_ctx_stack.top.flashes = session.session_info.flashes
            session.session_info.flashes = []

    return _request_ctx_stack.top.flashes
