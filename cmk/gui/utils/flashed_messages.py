#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Flashing messages to the next request.

Inspired by generic logic flask flashed messages, but implemented in a simpler way.
Flask uses a generic session cookie store which we don't want to implement here for
simplicity. In case we have such a generic thing, it will be easy to switch to it.
"""

# mypy: disable-error-code="exhaustive-match"

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

import flask

from cmk.gui.utils.escaping import escape_text
from cmk.gui.utils.html import HTML

MsgType = Literal["message", "waiting", "warning", "error", "info"]


def _parse_valid_msg_type(val: str) -> MsgType:
    match val:
        case "message" | "waiting" | "warning" | "error" | "info":
            return val
    return "message"


def flash(
    message: str | HTML,
    msg_type: MsgType = "message",
) -> None:
    """To handle both, HTML and str, correctly we need to

        a) escape the given str for HTML and
        b) cast the HTML objects to str.

    Before handing back the messages to the consumer, all need to converted back to HTML
    (see get_flashed_messages())
    """
    if isinstance(message, HTML):
        normalized = str(message)
    else:
        normalized = escape_text(message)
    flask.flash(normalized, msg_type)


@dataclass(frozen=True)
class FlashedMessageWithCategory:
    msg: HTML
    msg_type: MsgType


@dataclass(frozen=True)
class FlashedMessage:
    msg: HTML


def get_flashed_messages_with_categories() -> Sequence[FlashedMessageWithCategory]:
    """Return the messages flashed from the previous request to this one

    Move the flashes from the session object to the current request once and
    cache them for the current request.
    """
    return [
        FlashedMessageWithCategory(
            msg=HTML.without_escaping(flash_[1]),
            msg_type=_parse_valid_msg_type(flash_[0]),
        )
        for flash_ in flask.get_flashed_messages(with_categories=True)
        # The filtering is only there because get_flashed_messages returns a Union.
        if isinstance(flash_, tuple)
    ]


def get_flashed_messages() -> Sequence[FlashedMessage]:
    """Return the messages flashed from the previous request to this one

    Move the flashes from the session object to the current request once and
    cache them for the current request.
    """
    return [
        FlashedMessage(
            msg=HTML.without_escaping(flash_),
        )
        for flash_ in flask.get_flashed_messages(with_categories=False)
        # The filtering is only there because get_flashed_messages returns a Union.
        if isinstance(flash_, str)
    ]
