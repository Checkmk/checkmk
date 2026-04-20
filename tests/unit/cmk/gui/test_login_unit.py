#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="comparison-overlap"


from __future__ import annotations

import time
from base64 import b64encode
from collections.abc import Callable, Generator, Iterator
from datetime import datetime
from http.cookies import SimpleCookie
from typing import Literal

import flask
import pytest
from werkzeug.test import create_environ

from cmk.ccc.user import UserId
from cmk.gui import auth, http, login
from cmk.gui.config import active_config
from cmk.gui.http import request
from cmk.gui.logged_in import LoggedInNobody, LoggedInUser, user
from cmk.gui.script_helpers import application_and_request_context
from cmk.gui.session import session
from cmk.gui.type_defs import (
    SessionStateMachine,
    TwoFactorCredentials,
    UserSpec,
    WebAuthnCredential,
)
from cmk.gui.userdb import is_two_factor_login_enabled
from cmk.gui.userdb.session import auth_cookie_name, auth_cookie_value, generate_auth_hash
from cmk.gui.userdb.store import load_custom_attr, save_custom_attr, save_two_factor_credentials
from cmk.gui.utils.misc import saveint
from cmk.gui.utils.roles import UserPermissions
from cmk.livestatus_client.testing import MockLiveStatusConnection
from tests.testlib.gui.users import create_and_destroy_user
from tests.testlib.gui.web_test_app import WebTestAppForCMK


# copied from testlib.
# NOTE: you should not need this function in a unit test.
def wait_until(
    condition: Callable[[], bool],
    timeout: float = 1,
    interval: float = 0.1,
    condition_name: str = "",
) -> None:
    """Waits until a given condition is met (or timeout was reached -> TimeoutError).

    Args:
        condition (Callable[[], bool]): condition to be met. Will be called repeatedly until true.
        timeout (float, optional): Timeout in seconds. Defaults to 1.
        interval (float, optional): Time to wait (sleep) between checks. Defaults to 0.1.
        condition_name (str, optional): Name of the condition. Used for logging.

    Raises:
        TimeoutError: If the condition was not met within the given timeout.
    """
    condition_name = condition_name or repr(condition)

    start = now = time.time()
    while now - start <= timeout:
        if condition():
            return
        time.sleep(interval)
        now = time.time()

    error_message = f"Timeout waiting for '{condition_name}' to finish (Timeout: {timeout} sec)"
    raise TimeoutError(error_message)


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
    with create_and_destroy_user(custom_attrs=custom_attrs, config=active_config) as user_tuple:
        resp = wsgi_app.login(user_tuple[0], user_tuple[1])
        assert resp.status_code == 302
        assert resp.location.startswith("user_login_two_factor.py")


def test_login_forced_password_change(
    wsgi_app: WebTestAppForCMK, request_context: None, patch_theme: None
) -> None:
    custom_attrs: UserSpec = {
        "enforce_pw_change": True,
    }
    with create_and_destroy_user(custom_attrs=custom_attrs, config=active_config) as user_tuple:
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
    with create_and_destroy_user(custom_attrs=custom_attrs, config=active_config) as user_tuple:
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
        with login.authenticate(UserPermissions({}, {}, {}, [])) as authenticated:
            assert authenticated is True
            assert user.id == user_id

    assert user.id is None


def test_authenticate_fails(flask_app: flask.Flask, with_user: UserId) -> None:
    assert user.id is None

    with flask_app.test_request_context():
        with login.authenticate(UserPermissions({}, {}, {}, [])) as authenticated:
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
            with login.authenticate(UserPermissions({}, {}, {}, [])) as authenticated:
                assert authenticated is True
                assert user.id == user_id
                assert session.user.id == user.id

        with flask_app.request_context(create_environ()):
            flask_app.preprocess_request()
            assert user.id is None


@pytest.fixture(name="user_login")
def fixture_user_login(
    wsgi_app: WebTestAppForCMK,
    with_user: tuple[UserId, str],
) -> Iterator[WebTestAppForCMK]:
    """Define the operator to be used for validation, based on user's login status."""
    wsgi_app.login(*with_user)
    yield wsgi_app
    session.logout()


def test_auth_session_times(user_login: WebTestAppForCMK, auth_request: http.Request) -> None:
    wsgi_app_ = user_login
    wsgi_app_.get(auth_request)
    assert session.session_info.started_at is not None
    assert session.user.id == auth_request.environ["REMOTE_USER"]
    session_id = session.session_info.session_id
    started_at = session.session_info.started_at
    last_activity = session.session_info.last_activity

    wsgi_app_.get(auth_request)
    assert session.session_info.session_id == session_id
    assert session.session_info.started_at == started_at
    # tried it with time.sleep and ">".
    assert session.session_info.last_activity >= last_activity


def _validate_check_and_process_file_complete(expected_state: str) -> bool:
    return session.check_and_update_session_state() == expected_state


@pytest.mark.parametrize(
    "two_factor_creds, expected_state_two_factor_setting, expected_state",
    [
        pytest.param(
            {
                "webauthn_credentials": {},
                "backup_codes": [],
                "totp_credentials": {
                    "83deaab4-d3cc-4c43-8928-6f3da4c37f17": {
                        "credential_id": "83deaab4-d3cc-4c43-8928-6f3da4c37f17",
                        "secret": b"\xf4x\x13\x1d\x12g\t\xe6R\xa6",
                        "version": 1,
                        "registered_at": int(datetime.now().timestamp()),
                        "alias": "",
                    }
                },
            },
            True,
            "second_factor_auth_needed",
        ),
        pytest.param(
            {
                "webauthn_credentials": {},
                "backup_codes": [],
                "totp_credentials": {},
            },
            False,
            "logged_in",
        ),
    ],
)
def test_check_and_update_two_factor_auth(
    user_login: WebTestAppForCMK,
    auth_request: http.Request,
    two_factor_creds: TwoFactorCredentials,
    expected_state_two_factor_setting: bool,
    expected_state: str,
) -> None:
    try:
        session.logout()
        assert session.session_info.session_state == "credentials_needed"

        save_two_factor_credentials(session.user.ident, two_factor_creds)
        assert is_two_factor_login_enabled(session.user.ident) == expected_state_two_factor_setting
        wait_until(
            lambda: _validate_check_and_process_file_complete(expected_state=expected_state),
            timeout=10,
        )
    finally:
        save_two_factor_credentials(
            session.user.ident,
            {
                "webauthn_credentials": {},
                "backup_codes": [],
                "totp_credentials": {},
            },
        )
        session.logout()


def _validate_pw_change_file_saved(expected_password_change_setting: int) -> bool:
    save_custom_attr(session.user.ident, "enforce_pw_change", str(expected_password_change_setting))
    return (
        load_custom_attr(user_id=session.user.ident, key="enforce_pw_change", parser=saveint)
        == expected_password_change_setting
    )


@pytest.mark.parametrize(
    "expected_password_change_setting, expected_state",
    [
        pytest.param(
            1,
            "password_change_needed",
        ),
        pytest.param(
            0,
            "logged_in",
        ),
    ],
)
def test_check_and_update_password_change(
    user_login: WebTestAppForCMK,
    auth_request: http.Request,
    expected_password_change_setting: int,
    expected_state: str,
) -> None:
    try:
        session.logout()
        assert session.session_info.session_state == "credentials_needed"

        wait_until(
            lambda: _validate_pw_change_file_saved(expected_password_change_setting), timeout=10
        )
        wait_until(
            lambda: _validate_check_and_process_file_complete(expected_state=expected_state),
            timeout=10,
        )
    finally:
        wait_until(lambda: _validate_pw_change_file_saved(0), timeout=10)
        session.logout()


def simplified_auth_check_true() -> bool:
    return True


def simplified_auth_check_false() -> bool:
    return False


@pytest.mark.parametrize(
    "two_fa_auth_needed, two_fa_setup_needed, pw_changed_needed, starting_state, expected_state",
    [
        pytest.param(
            simplified_auth_check_true,
            simplified_auth_check_false,
            simplified_auth_check_false,
            "credentials_needed",
            "second_factor_auth_needed",
            id="cn_to_sfan_auth_set",
        ),
        pytest.param(
            simplified_auth_check_true,
            simplified_auth_check_true,
            simplified_auth_check_false,
            "credentials_needed",
            "second_factor_auth_needed",
            id="cn_to_sfan_auth_setup_set",
        ),
        pytest.param(
            simplified_auth_check_true,
            simplified_auth_check_true,
            simplified_auth_check_true,
            "credentials_needed",
            "second_factor_auth_needed",
            id="cn_to_sfan_auth_setup_password_set",
        ),
        pytest.param(
            simplified_auth_check_false,
            simplified_auth_check_true,
            simplified_auth_check_false,
            "credentials_needed",
            "second_factor_setup_needed",
            id="cn_to_sfsn_setup_set",
        ),
        pytest.param(
            simplified_auth_check_false,
            simplified_auth_check_true,
            simplified_auth_check_true,
            "credentials_needed",
            "second_factor_setup_needed",
            id="cn_to_sfsn_setup_password_set",
        ),
        pytest.param(
            simplified_auth_check_false,
            simplified_auth_check_false,
            simplified_auth_check_true,
            "credentials_needed",
            "password_change_needed",
            id="cn_to_pcn_password_set",
        ),
        pytest.param(
            simplified_auth_check_true,
            simplified_auth_check_false,
            simplified_auth_check_false,
            "second_factor_auth_needed",
            "logged_in",
            id="sfan_to_li_auth_set",
        ),
        pytest.param(
            simplified_auth_check_true,
            simplified_auth_check_true,
            simplified_auth_check_false,
            "second_factor_auth_needed",
            "logged_in",
            id="sfan_to_li_auth_setup_set",
        ),
        pytest.param(
            simplified_auth_check_true,
            simplified_auth_check_true,
            simplified_auth_check_true,
            "second_factor_auth_needed",
            "password_change_needed",
            id="sfan_to_pcn_auth_setup_password_set",
        ),
        pytest.param(
            simplified_auth_check_false,
            simplified_auth_check_true,
            simplified_auth_check_true,
            "second_factor_auth_needed",
            "password_change_needed",
            id="sfan_to_pcn_setup_password_set",
        ),
        pytest.param(
            simplified_auth_check_false,
            simplified_auth_check_false,
            simplified_auth_check_true,
            "second_factor_auth_needed",
            "password_change_needed",
            id="sfan_to_pcn_password_set",
        ),
        pytest.param(
            simplified_auth_check_true,
            simplified_auth_check_false,
            simplified_auth_check_false,
            "second_factor_setup_needed",
            "logged_in",
            id="sfsn_to_li_auth_set",
        ),
        pytest.param(
            simplified_auth_check_true,
            simplified_auth_check_true,
            simplified_auth_check_false,
            "second_factor_setup_needed",
            "logged_in",
            id="sfsn_to_li_auth_setup_set",
        ),
        pytest.param(
            simplified_auth_check_true,
            simplified_auth_check_true,
            simplified_auth_check_true,
            "second_factor_setup_needed",
            "password_change_needed",
            id="sfsn_to_pcn_auth_setup_password_set",
        ),
        pytest.param(
            simplified_auth_check_false,
            simplified_auth_check_true,
            simplified_auth_check_true,
            "second_factor_setup_needed",
            "password_change_needed",
            id="sfsn_to_pcn_setup_password_set",
        ),
        pytest.param(
            simplified_auth_check_false,
            simplified_auth_check_false,
            simplified_auth_check_true,
            "second_factor_setup_needed",
            "password_change_needed",
            id="sfsn_to_pcn_password_set",
        ),
        pytest.param(
            simplified_auth_check_true,
            simplified_auth_check_false,
            simplified_auth_check_false,
            "password_change_needed",
            "logged_in",
            id="pcn_to_li_auth_set",
        ),
        pytest.param(
            simplified_auth_check_true,
            simplified_auth_check_true,
            simplified_auth_check_false,
            "password_change_needed",
            "logged_in",
            id="pcn_to_li_auth_setup_set",
        ),
        pytest.param(
            simplified_auth_check_true,
            simplified_auth_check_true,
            simplified_auth_check_true,
            "password_change_needed",
            "logged_in",
            id="pcn_to_li_auth_setup_password_set",
        ),
        pytest.param(
            simplified_auth_check_false,
            simplified_auth_check_true,
            simplified_auth_check_true,
            "password_change_needed",
            "logged_in",
            id="pcn_to_li_setup_password_set",
        ),
        pytest.param(
            simplified_auth_check_false,
            simplified_auth_check_false,
            simplified_auth_check_true,
            "password_change_needed",
            "logged_in",
            id="pcn_to_li_password_set",
        ),
        pytest.param(
            simplified_auth_check_false,
            simplified_auth_check_false,
            simplified_auth_check_false,
            "credentials_needed",
            "logged_in",
            id="cn_to_li_none_set",
        ),
        pytest.param(
            simplified_auth_check_false,
            simplified_auth_check_false,
            simplified_auth_check_false,
            "second_factor_auth_needed",
            "logged_in",
            id="sfan_to_li_none_set",
        ),
        pytest.param(
            simplified_auth_check_false,
            simplified_auth_check_false,
            simplified_auth_check_false,
            "second_factor_setup_needed",
            "logged_in",
            id="sfsn_to_li_none_set",
        ),
        pytest.param(
            simplified_auth_check_false,
            simplified_auth_check_false,
            simplified_auth_check_false,
            "password_change_needed",
            "logged_in",
            id="pcn_to_li_none_set",
        ),
    ],
)
def test_state_transition_flow_logic(
    user_login: WebTestAppForCMK,
    auth_request: http.Request,
    two_fa_auth_needed: Callable[[], bool],
    two_fa_setup_needed: Callable[[], bool],
    pw_changed_needed: Callable[[], bool],
    starting_state: Literal[
        "credentials_needed",
        "password_change_needed",
        "logged_in",
        "second_factor_setup_needed",
        "second_factor_auth_needed",
    ],
    expected_state: Literal[
        "credentials_needed",
        "password_change_needed",
        "logged_in",
        "second_factor_setup_needed",
        "second_factor_auth_needed",
    ],
) -> None:
    try:
        session.logout()
        assert session.session_info.session_state == "credentials_needed"

        state = session.session_info.session_state = starting_state
        ssm = SessionStateMachine(state)
        assert (
            ssm.transition(
                check_if_2fa_auth_is_needed=two_fa_auth_needed,
                check_if_2fa_setup_is_needed=two_fa_setup_needed,
                check_if_pw_change_is_needed=pw_changed_needed,
            )
            == expected_state
        )
    finally:
        session.logout()


def test_state_transition_invalid_state(
    user_login: WebTestAppForCMK,
    auth_request: http.Request,
) -> None:
    try:
        session.logout()
        assert session.session_info.session_state == "credentials_needed"

        state = session.session_info.session_state = "no_a_real_state"  # type: ignore[assignment] # As we are forcing a value not in the Literal

        with pytest.raises(ValueError):
            ssm = SessionStateMachine(state)  # type: ignore[arg-type]  # As we are forcing a value not in the Literal
            ssm.transition(
                check_if_2fa_auth_is_needed=simplified_auth_check_true,
                check_if_2fa_setup_is_needed=simplified_auth_check_true,
                check_if_pw_change_is_needed=simplified_auth_check_true,
            )
    finally:
        session.logout()
