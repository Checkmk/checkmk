#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import Any

import pytest

from cmk.ccc.user import UserId

from cmk.gui.message import _parse_message, Message, MessageText


@pytest.mark.parametrize(
    "message, result",
    [
        pytest.param(
            dict(
                text="Text",
                dest=("list", [UserId("bar")]),
                methods=[],
                valid_till=456,
                id="ID",
                time=123,
            ),
            Message(
                text=MessageText(content_type="text", content="Text"),
                dest=("list", [UserId("bar")]),
                methods=[],
                valid_till=456,
                id="ID",
                time=123,
                security=False,
                acknowledged=False,
            ),
            id="v0",
        ),
        pytest.param(
            dict(
                text="Text",
                dest=("list", [UserId("bar")]),
                methods=[],
                valid_till=456,
                id="ID",
                time=123,
                security=False,
                acknowledged=False,
            ),
            Message(
                text=MessageText(content_type="text", content="Text"),
                dest=("list", [UserId("bar")]),
                methods=[],
                valid_till=456,
                id="ID",
                time=123,
                security=False,
                acknowledged=False,
            ),
            id="v0-sec-ack-false",
        ),
        pytest.param(
            dict(
                text="Text",
                dest=("list", [UserId("bar")]),
                methods=[],
                valid_till=456,
                id="ID",
                time=123,
                security=True,
                acknowledged=True,
            ),
            Message(
                text=MessageText(content_type="text", content="Text"),
                dest=("list", [UserId("bar")]),
                methods=[],
                valid_till=456,
                id="ID",
                time=123,
                security=True,
                acknowledged=True,
            ),
            id="v0-sec-ack-true",
        ),
        pytest.param(
            dict(
                text=MessageText(content_type="html", content="<h>Text</h>"),
                dest=("list", [UserId("bar")]),
                methods=[],
                valid_till=456,
                id="ID",
                time=123,
                security=False,
                acknowledged=False,
            ),
            Message(
                text=MessageText(content_type="html", content="<h>Text</h>"),
                dest=("list", [UserId("bar")]),
                methods=[],
                valid_till=456,
                id="ID",
                time=123,
                security=False,
                acknowledged=False,
            ),
            id="html",
        ),
    ],
)
def test__parse_message(message: Mapping[str, Any], result: Message) -> None:
    assert _parse_message(message) == result
