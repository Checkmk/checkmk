#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import cast

import pytest

from cmk.gui import message
from cmk.gui.message import Message
from cmk.gui.user_message import show_user_messages
from cmk.gui.utils.output_funnel import output_funnel


def _message(msg_id: str, timestamp: int, **extra: object) -> Message:
    # Cast because the point of these tests is a stored message that does NOT
    # carry every key the TypedDict promises.
    return cast(
        Message,
        {
            "id": msg_id,
            "time": timestamp,
            "text": {"content_type": "text", "content": f"content of {msg_id}"},
            "dest": ("all",),
            "methods": ["gui_hint"],
            "valid_till": None,
            "acknowledged": False,
            **extra,
        },
    )


@pytest.mark.usefixtures("request_context", "patch_theme")
def test_show_user_messages_with_message_lacking_the_security_flag(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # A message stored before the security flag existed has no "security" key at all,
    # while a newer one does. Sorting the two together must still work.
    messages = [
        _message("legacy", 100),
        _message("recent", 200, security=True),
    ]
    monkeypatch.setattr(message, "get_gui_messages", lambda *_a, **_kw: messages)

    with output_funnel.plugged():
        show_user_messages()
        rendered = "".join(output_funnel.drain())

    assert "content of legacy" in rendered
    assert "content of recent" in rendered
