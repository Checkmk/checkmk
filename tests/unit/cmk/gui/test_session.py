#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest
from flask import Flask, request
from pytest_mock import MockerFixture

from cmk.gui.logged_in import LoggedInUser
from cmk.gui.session import FileBasedSession


@pytest.mark.parametrize(
    "cookie",
    (
        None,
        "auth_NO_SITE=foo:00000000-0000-0000-0000-000000000000:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
    ),
)
def test_new_session_with_invalid_cookie(
    mocker: MockerFixture, flask_app: Flask, cookie: None | str
) -> None:
    """We had a regression where authentication via header does not work if an invalid cookie exists. This is a test for that"""
    headers = {}
    if cookie:
        headers["Cookie"] = cookie

    with flask_app.test_request_context(
        headers=headers,
        environ_overrides={
            "REMOTE_USER": "foo",
        },
    ):
        # The user must be present, quickest way is patching ;-)
        mocker.patch("cmk.gui.userdb.user_exists", lambda _userid: True)
        session = FileBasedSession().open_session(flask_app, request)
    assert session is not None
    assert session.exc is None
    assert isinstance(session.user, LoggedInUser)
