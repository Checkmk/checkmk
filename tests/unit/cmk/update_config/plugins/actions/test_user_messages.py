#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.ccc.user import UserId
from cmk.update_config.plugins.actions.user_messages import MigrateUserMessages


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
            dict(
                text=dict(content_type="text", content="Text"),
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
            dict(
                text=dict(content_type="text", content="Text"),
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
            dict(
                text=dict(content_type="text", content="Text"),
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
                text=dict(content_type="html", content="<h>Text</h>"),
                dest=("list", [UserId("bar")]),
                methods=[],
                valid_till=456,
                id="ID",
                time=123,
                security=False,
                acknowledged=False,
            ),
            dict(
                text=dict(content_type="html", content="<h>Text</h>"),
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
def test_migrate(message: object, result: object) -> None:
    assert MigrateUserMessages.migrate(message) == result
