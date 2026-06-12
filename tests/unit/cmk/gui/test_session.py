#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time

import pytest
from flask import Flask, request
from pytest_mock import MockerFixture

from cmk.ccc.site import omd_site
from cmk.ccc.user import UserId
from cmk.gui.logged_in import LoggedInUser
from cmk.gui.session import FileBasedSession
from cmk.gui.type_defs import SessionInfo
from cmk.gui.userdb.session import (
    auth_cookie_value,
    create_session_id,
    save_session_infos,
)
from cmk.gui.userdb.store import save_custom_attr
from tests.testlib.gui.web_test_app import SetConfig


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


def test_valid_cookie_under_foreign_site_name_is_not_resumed(
    flask_app: Flask, with_user: tuple[UserId, str]
) -> None:
    """The auth cookie is site-scoped — a valid session value under another site's cookie name (``auth_<omd_site>``) is never resumed."""
    user_id, _password = with_user
    own_cookie_name = FileBasedSession().get_cookie_name(flask_app)
    assert own_cookie_name == f"auth_{omd_site()}"

    # A genuinely valid, logged-in session for the current site.
    session_id = create_session_id()
    now = int(time.time())
    save_session_infos(
        user_id,
        {
            session_id: SessionInfo(
                session_id=session_id,
                started_at=now,
                last_activity=now,
                auth_type="cookie",
                session_state="logged_in",
            )
        },
    )
    cookie_value = auth_cookie_value(user_id, session_id)

    # Control: under the site's own cookie name the session resumes.
    with flask_app.test_request_context(headers={"Cookie": f"{own_cookie_name}={cookie_value}"}):
        resumed = FileBasedSession().open_session(flask_app, request)
    assert resumed is not None
    assert resumed.exc is None
    assert resumed.session_info.session_id == session_id

    # Same valid value under another site's cookie name must be ignored.
    with flask_app.test_request_context(headers={"Cookie": f"auth_some_other_site={cookie_value}"}):
        foreign = FileBasedSession().open_session(flask_app, request)
    assert foreign is not None
    assert foreign.exc is not None, (
        "A cookie carrying another site's name was honoured by this site — "
        "auth cookies must be site-scoped (auth_<omd_site>)."
    )


def test_session_revoked_after_user_locked_post_auth(
    flask_app: Flask, with_user: tuple[UserId, str]
) -> None:
    """Locking a user after they authenticated revokes their session.

    Locking an account bumps its auth serial (``cmk/gui/wato/pages/users.py``); because
    the cookie's hash binds that serial (``generate_auth_hash``), a cookie issued before
    the lock no longer validates, so the next request must re-authenticate.
    """
    user_id, _password = with_user
    cookie_name = FileBasedSession().get_cookie_name(flask_app)

    session_id = create_session_id()
    now = int(time.time())
    save_session_infos(
        user_id,
        {
            session_id: SessionInfo(
                session_id=session_id,
                started_at=now,
                last_activity=now,
                auth_type="cookie",
                session_state="logged_in",
            )
        },
    )
    cookie_value = auth_cookie_value(user_id, session_id)

    with flask_app.test_request_context(headers={"Cookie": f"{cookie_name}={cookie_value}"}):
        before_lock = FileBasedSession().open_session(flask_app, request)
    assert before_lock is not None
    assert before_lock.exc is None
    assert before_lock.session_info.session_id == session_id

    # The persisted state change a lock makes: increment the user's auth serial.
    save_custom_attr(user_id, "serial", "1")

    with flask_app.test_request_context(headers={"Cookie": f"{cookie_name}={cookie_value}"}):
        after_lock = FileBasedSession().open_session(flask_app, request)
    assert after_lock is not None
    assert after_lock.exc is not None, (
        "A session cookie issued before the user was locked was still honoured — "
        "locking must bump the auth serial and invalidate outstanding cookies."
    )


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
