#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Flashing messages to the next request.

Inspired by generic logic flask flashed messages, but implemented in a simpler way.
Flask uses a generic session cookie store which we don't want to implement here for
simplicity. In case we have such a generic thing, it will be easy to switch to it.
"""

from typing import get_args, Literal, NamedTuple, TypeGuard

import flask

from cmk.gui.utils.escaping import escape_text
from cmk.gui.utils.html import HTML
from cmk.gui.utils.speaklater import LazyString


def flash(
    message: str | HTML | LazyString,
    msg_type: Literal["message", "warning", "error"] = "message",
) -> None:
    """To handle both, HTML and str, correctly we need to

        a) escape the given str for HTML and
        b) cast the HTML objects to str.

    Before handing back the messages to the consumer, all need to converted back to HTML
    (see get_flashed_messages())
    """
    if isinstance(message, str):
        normalized = escape_text(message)
    else:
        normalized = str(message)
    flask.flash(normalized, msg_type)


MSG_TYPET = Literal["message", "warning", "error"]


class FlashedMessage(NamedTuple):
    msg: HTML
    msg_type: MSG_TYPET


def _is_valid_msg_type(val: str) -> TypeGuard[MSG_TYPET]:
    return val in list(get_args(MSG_TYPET))


def get_flashed_messages(
    with_categories: bool = False,
) -> list[FlashedMessage]:
    """Return the messages flashed from the previous request to this one

    Move the flashes from the session object to the current request once and
    cache them for the current request.
    """
    # NOTE
    # This whole loop/if is only there because get_flashed_messages returns a Union.
    # If the flask developers were to put in proper @overloads, we can simplify here.
    result = []
    for _flash in flask.get_flashed_messages(with_categories):
        if isinstance(_flash, tuple):
            msg_type = _flash[0]
            assert _is_valid_msg_type(msg_type)
            result.append(FlashedMessage(msg=HTML.without_escaping(_flash[1]), msg_type=msg_type))
        else:
            result.append(FlashedMessage(msg=HTML.without_escaping(_flash), msg_type="message"))
    return result
