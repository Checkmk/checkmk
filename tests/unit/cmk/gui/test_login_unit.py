#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from __future__ import annotations

from base64 import b64encode
from collections.abc import Generator, Iterator
from http.cookies import SimpleCookie

import flask
import pytest
from werkzeug.test import create_environ

from tests.unit.cmk.gui.users import create_and_destroy_user
from tests.unit.cmk.web_test_app import WebTestAppForCMK

from cmk.ccc.user import UserId

from cmk.utils.livestatus_helpers.testing import MockLiveStatusConnection

from cmk.gui import auth, http, login
from cmk.gui.config import load_config
from cmk.gui.http import request
from cmk.gui.logged_in import LoggedInNobody, LoggedInUser, user
from cmk.gui.session import session
from cmk.gui.type_defs import UserSpec, WebAuthnCredential
from cmk.gui.userdb.session import auth_cookie_name, auth_cookie_value, generate_auth_hash
from cmk.gui.utils.script_helpers import application_and_request_context


@pytest.fixture(name="user_id")
def fixture_user_id(with_user: tuple[UserId, str]) -> UserId:
    return with_user[0]


def test_login_two_factor_redirect(
    wsgi_app: WebTestAppForCMK, request_context: None, patch_theme: None
) -> None:
    auth_struct: WebAuthnCredential = {
        "credential_id": "Yaddayadda!",
        "registered_at": 0,
        "alias": "Yaddayadda!",
        "credential_data": b"",
    }
    custom_attrs: UserSpec = {
        "two_factor_credentials": {
            "webauthn_credentials": {"foo": auth_struct},
            "backup_codes": [],
            "totp_credentials": {},
        },
    }
    with create_and_destroy_user(custom_attrs=custom_attrs) as user_tuple:
        resp = wsgi_app.login(user_tuple[0], user_tuple[1])
        assert resp.status_code == 302
        assert resp.location.startswith("user_login_two_factor.py")


def test_login_forced_password_change(
    wsgi_app: WebTestAppForCMK, request_context: None, patch_theme: None
) -> None:
    custom_attrs: UserSpec = {
        "enforce_pw_change": True,
    }
    with create_and_destroy_user(custom_attrs=custom_attrs) as user_tuple:
        resp = wsgi_app.login(user_tuple[0], user_tuple[1])
        assert resp.status_code == 302
        assert resp.location.startswith("user_change_pw.py")


def test_login_two_factor_has_precedence_over_password_change(
    wsgi_app: WebTestAppForCMK, request_context: None, patch_theme: None
) -> None:
    auth_struct: WebAuthnCredential = {
        "credential_id": "Yaddayadda!",
        "registered_at": 0,
        "alias": "Yaddayadda!",
        "credential_data": b"",
    }
    custom_attrs: UserSpec = {
        "enforce_pw_change": True,
        "two_factor_credentials": {
            "webauthn_credentials": {"foo": auth_struct},
            "backup_codes": [],
            "totp_credentials": {},
        },
    }
    with create_and_destroy_user(custom_attrs=custom_attrs) as user_tuple:
        resp = wsgi_app.login(user_tuple[0], user_tuple[1])
        assert resp.status_code == 302
        assert resp.location.startswith("user_login_two_factor.py")


def test_login_with_cookies(
    wsgi_app: WebTestAppForCMK,
    with_user: tuple[UserId, str],
    mock_livestatus: MockLiveStatusConnection,
    patch_theme: None,
) -> None:
    # We will be redirected to the login page
    response = wsgi_app.get("/NO_SITE/check_mk/")
    login_page_url = response.location
    assert login_page_url.startswith("/NO_SITE/check_mk/login.py")

    # We see if we can access the login page.
    response = wsgi_app.get(login_page_url)
    assert response.status_code == 200

    # We try to log in
    response = wsgi_app.post(
        login_page_url,
        params={"_username": with_user[0], "_password": with_user[1], "_login": "Login"},
    )
    index_page = response.location
    assert index_page.endswith("index.py")  # Relative redirect to "index.py" :-( !!!
    response = wsgi_app.get("/NO_SITE/check_mk/index.py")
    assert response.status_code == 200

    test_environ = create_environ("/NO_SITE/", method="GET")
    wsgi_app._add_cookies_to_wsgi(test_environ)

    # request context with cookie yields a user
    assert session.user.id == with_user[0]

    # request context without this cookie yields nobody
    with application_and_request_context(dict(create_environ())):
        assert isinstance(session.user, LoggedInNobody)
        assert session.user.id != with_user[0]


# TODO: to be moved out of REST API blueprint to global in a later commit.
def test_login_with_bearer_token(with_user: tuple[UserId, str], flask_app: flask.Flask) -> None:
    with flask_app.test_request_context(
        "/", method="GET", headers={"Authorization": f"Bearer {with_user[0]} {with_user[1]}"}
    ):
        assert type(session.user) is LoggedInUser
        assert session.user.id == with_user[0]


def test_login_with_basic_auth(with_user: tuple[UserId, str], flask_app: flask.Flask) -> None:
    token = b64encode(f"{with_user[0]}:{with_user[1]}".encode()).decode()
    with flask_app.test_request_context(
        "/", method="GET", headers={"Authorization": f"Basic {token}"}
    ):
        assert type(session.user) is LoggedInUser
        assert session.user.id == with_user[0]


def test_login_with_webserver(with_user: tuple[UserId, str], flask_app: flask.Flask) -> None:
    with flask_app.test_request_context(
        "/",
        method="GET",
        environ_overrides={"REMOTE_USER": with_user[0]},
    ):
        assert type(session.user) is LoggedInUser
        assert session.user.id == with_user[0]


def test_authenticate_success(flask_app: flask.Flask, user_id: UserId) -> None:
    assert user.id is None

    with flask_app.test_request_context(
        environ_overrides={"REMOTE_USER": user_id},
    ):
        flask_app.preprocess_request()
        with login.authenticate() as authenticated:
            assert authenticated is True
            assert user.id == user_id

    assert user.id is None


def test_authenticate_fails(flask_app: flask.Flask, with_user: UserId) -> None:
    assert user.id is None

    with flask_app.test_request_context():
        with login.authenticate() as authenticated:
            assert authenticated is False
            assert user.id is None

    assert user.id is None


@pytest.fixture(name="pre_16_cookie")
def fixture_pre_16_cookie() -> Iterator[str]:
    environ = dict(
        create_environ(),
        HTTP_COOKIE="xyz=123; auth_stable=lärs:1534272374.61:1f59cac3fcd5bcc389e4f8397bed315b; abc=123".encode(),
    )

    with application_and_request_context(environ):
        yield "auth_stable"


@pytest.fixture(name="pre_20_cookie")
def fixture_pre_20_cookie() -> Iterator[str]:
    environ = dict(
        create_environ(),
        HTTP_COOKIE="xyz=123; auth_stable=lärs:1534272374.61:1f59cac3fcd5bcc389e4f8397bed315b; abc=123".encode(),
    )

    with application_and_request_context(environ):
        yield "auth_stable"


@pytest.fixture(name="session_id")
def fixture_session_id(flask_app: flask.Flask, with_user: tuple[UserId, str]) -> Generator[str]:
    with flask_app.test_request_context(
        environ_overrides={"REMOTE_USER": with_user[0]},
    ):
        flask_app.preprocess_request()
        assert session.user.id == with_user[0]
        session_id = session.session_info.session_id
        # Finalize the response to allow the session to be persisted and the cookie to be set.
        response = flask_app.process_response(http.Response())

    # Extract the cookie and prepare a request header
    cookie: SimpleCookie = SimpleCookie(response.headers["Set-Cookie"])
    cookie_headers = [cookie.output(header="Cookie").split(" ", 1)]

    with flask_app.test_request_context(headers=cookie_headers):
        flask_app.preprocess_request()
        # We ensure that the cookie has been sent along.
        cookie_name = list(cookie.keys())[0]
        assert request.cookies[cookie_name] == list(cookie.values())[0].value

        yield session_id


@pytest.fixture(name="current_cookie")
def fixture_current_cookie(with_user: tuple[UserId, str], session_id: str) -> Iterator[str]:
    user_id = with_user[0]
    cookie_name = auth_cookie_name()
    cookie_value = auth_cookie_value(user_id, session_id)

    environ = {**create_environ(), "HTTP_COOKIE": f"{cookie_name}={cookie_value}"}

    with application_and_request_context(environ):
        load_config()
        yield cookie_name


def test_parse_auth_cookie_allow_current(
    current_cookie: str, with_user: tuple[UserId, str], session_id: str
) -> None:
    assert (cookie := request.cookies.get(current_cookie, type=str))
    assert auth.parse_and_check_cookie(cookie) == (
        with_user[0],
        session_id,
        generate_auth_hash(with_user[0], session_id),
    )


def test_web_server_auth_session(flask_app: flask.Flask, user_id: UserId) -> None:
    environ = dict(create_environ(), REMOTE_USER=str(user_id))

    with flask_app.app_context():
        with flask_app.request_context(create_environ()):
            flask_app.preprocess_request()
            assert user.id is None

        with flask_app.request_context(environ):
            flask_app.preprocess_request()
            with login.authenticate() as authenticated:
                assert authenticated is True
                assert user.id == user_id
                assert session.user.id == user.id

        with flask_app.request_context(create_environ()):
            flask_app.preprocess_request()
            assert user.id is None


def test_auth_session_times(wsgi_app: WebTestAppForCMK, auth_request: http.Request) -> None:
    wsgi_app.get(auth_request)
    assert session.session_info.started_at is not None
    assert session.user.id == auth_request.environ["REMOTE_USER"]
    session_id = session.session_info.session_id
    started_at = session.session_info.started_at
    last_activity = session.session_info.last_activity

    wsgi_app.get(auth_request)
    assert session.session_info.session_id == session_id
    assert session.session_info.started_at == started_at
    # tried it with time.sleep and ">".
    assert session.session_info.last_activity >= last_activity
