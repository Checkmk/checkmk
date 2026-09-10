#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from datetime import datetime, timedelta, UTC

import pytest
from flask import Flask, request
from pytest_mock import MockerFixture

from cmk.ccc.user import UserId
from cmk.gui.logged_in import LoggedInUser
from cmk.gui.oauth.store.client_store import get_client_store
from cmk.gui.oauth.store.token_store import get_token_store
from cmk.gui.scopes import DEFAULT_SCOPE
from cmk.gui.session import FileBasedSession
from cmk.gui.userdb.store import save_two_factor_credentials
from tests.unit.cmk.web_test_app import SetConfig


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


def test_automation_user_exempt_from_2fa_enforcement(
    flask_app: Flask,
    with_automation_user: tuple[UserId, str],
    set_config: SetConfig,
) -> None:
    """Automation users cannot perform 2FA, so global enforcement must not block them."""
    user_id, secret = with_automation_user
    with (
        set_config(require_two_factor_all_users=True),
        flask_app.test_request_context(
            headers={"Authorization": f"Bearer {user_id} {secret}"},
        ),
    ):
        sess = FileBasedSession().open_session(flask_app, request)
    assert sess is not None
    assert sess.session_info.session_state == "logged_in"


def test_human_user_still_requires_2fa_setup_when_enforced(
    flask_app: Flask,
    with_user: tuple[UserId, str],
    set_config: SetConfig,
) -> None:
    """Human REST-API users are NOT exempted from enforcement."""
    user_id, password = with_user
    with (
        set_config(require_two_factor_all_users=True),
        flask_app.test_request_context(
            headers={"Authorization": f"Bearer {user_id} {password}"},
        ),
    ):
        sess = FileBasedSession().open_session(flask_app, request)
    assert sess is not None
    assert sess.session_info.session_state == "second_factor_setup_needed"


def test_oauth_token_exempt_from_2fa_check(
    flask_app: Flask,
    with_user: tuple[UserId, str],
) -> None:
    """A valid OAuth access token must not be blocked as needing a second factor.

    The token is only ever handed out after the user completed an interactive,
    2FA-gated /authorize consent step, so re-running that check per API request
    would apply it to a credential that already proves it was satisfied.
    """
    user_id, _password = with_user
    save_two_factor_credentials(
        user_id,
        {
            "webauthn_credentials": {},
            "backup_codes": [],
            "totp_credentials": {
                "83deaab4-d3cc-4c43-8928-6f3da4c37f17": {
                    "credential_id": "83deaab4-d3cc-4c43-8928-6f3da4c37f17",
                    "secret": b"\xf4x\x13\x1d\x12g\t\xe6R\xa6",
                    "version": 1,
                    "registered_at": int(time.time()),
                    "alias": "",
                }
            },
        },
    )

    with get_client_store() as client_store:
        registration = client_store.register(["https://client.example/callback"], None)
    assert registration.is_ok()

    with get_token_store() as token_store:
        issued = token_store.issue_token(
            user_id,
            expires_at=datetime.now(UTC) + timedelta(minutes=5),
            resource=None,
            scope=DEFAULT_SCOPE,
            client_id=registration.ok.client_id,
        )
    assert issued.is_ok()

    with flask_app.test_request_context(headers={"Authorization": f"Bearer {issued.ok}"}):
        sess = FileBasedSession().open_session(flask_app, request)
    assert sess is not None
    assert sess.session_info.session_state == "logged_in"
