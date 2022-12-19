#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime

import pytest
from werkzeug.test import create_environ

from tests.testlib.users import create_and_destroy_user

from tests.unit.cmk.gui.conftest import WebTestAppForCMK

from cmk.utils.type_defs import UserId

import cmk.gui.login as login
from cmk.gui.config import load_config
from cmk.gui.exceptions import MKAuthException
from cmk.gui.http import request
from cmk.gui.logged_in import user
from cmk.gui.type_defs import UserSpec, WebAuthnCredential
from cmk.gui.userdb import active_user_session
from cmk.gui.userdb.session import (
    _initialize_session,
    auth_cookie_name,
    auth_cookie_value,
    generate_auth_hash,
)
from cmk.gui.utils.script_helpers import application_and_request_context
from cmk.gui.utils.transaction_manager import transactions


@pytest.fixture(name="user_id")
def fixture_user_id(with_user: tuple[UserId, str]) -> UserId:
    return with_user[0]


def test_login_two_factor_redirect(wsgi_app: WebTestAppForCMK) -> None:
    auth: WebAuthnCredential = {
        "credential_id": "Yaddayadda!",
        "registered_at": 0,
        "alias": "Yaddayadda!",
        "credential_data": b"",
    }
    custom_attrs: UserSpec = {
        "two_factor_credentials": {"webauthn_credentials": {"foo": auth}, "backup_codes": []},
    }
    with create_and_destroy_user(custom_attrs=custom_attrs) as user_tuple:
        resp = wsgi_app.login(user_tuple[0], user_tuple[1])
        assert resp.status_code == 302
        assert resp.location.startswith("user_login_two_factor.py")


def test_login_forced_password_change(wsgi_app: WebTestAppForCMK) -> None:
    custom_attrs: UserSpec = {
        "enforce_pw_change": True,
    }
    with create_and_destroy_user(custom_attrs=custom_attrs) as user_tuple:
        resp = wsgi_app.login(user_tuple[0], user_tuple[1])
        assert resp.status_code == 302
        assert resp.location.startswith("user_change_pw.py")


def test_login_two_factor_has_precedence_over_password_change(wsgi_app: WebTestAppForCMK) -> None:
    auth: WebAuthnCredential = {
        "credential_id": "Yaddayadda!",
        "registered_at": 0,
        "alias": "Yaddayadda!",
        "credential_data": b"",
    }
    custom_attrs: UserSpec = {
        "enforce_pw_change": True,
        "two_factor_credentials": {"webauthn_credentials": {"foo": auth}, "backup_codes": []},
    }
    with create_and_destroy_user(custom_attrs=custom_attrs) as user_tuple:
        resp = wsgi_app.login(user_tuple[0], user_tuple[1])
        assert resp.status_code == 302
        assert resp.location.startswith("user_login_two_factor.py")


def test_authenticate_success(
    request_context: None, monkeypatch: pytest.MonkeyPatch, user_id: UserId
) -> None:
    monkeypatch.setattr(login, "_check_auth", lambda r: user_id)
    assert user.id is None
    with login.authenticate(request) as authenticated:
        assert authenticated is True
        assert user.id == user_id
    assert user.id is None


def test_authenticate_fails(
    request_context: None, monkeypatch: pytest.MonkeyPatch, user_id: UserId
) -> None:
    monkeypatch.setattr(login, "_check_auth", lambda r: None)
    assert user.id is None
    with login.authenticate(request) as authenticated:
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
def fixture_session_id(with_user: tuple[UserId, str]) -> str:
    now = datetime.now()
    user_id = with_user[0]
    return _initialize_session(user_id, now)


@pytest.fixture(name="current_cookie")
def fixture_current_cookie(with_user: tuple[UserId, str], session_id: str) -> Iterator[str]:
    user_id = with_user[0]
    cookie_name = auth_cookie_name()
    cookie_value = auth_cookie_value(user_id, session_id)

    environ = dict(create_environ(), HTTP_COOKIE=f"{cookie_name}={cookie_value}".encode())

    with application_and_request_context(environ):
        load_config()
        yield cookie_name


def test_parse_auth_cookie_refuse_pre_16(pre_16_cookie: str) -> None:
    with pytest.raises(MKAuthException, match="Refusing pre 2.0"):
        login.user_from_cookie(login._fetch_cookie(pre_16_cookie))


def test_parse_auth_cookie_refuse_pre_20(pre_20_cookie: str) -> None:
    with pytest.raises(MKAuthException, match="Refusing pre 2.0"):
        login.user_from_cookie(login._fetch_cookie(pre_20_cookie))


def test_parse_auth_cookie_allow_current(
    current_cookie: str, with_user: tuple[UserId, str], session_id: str
) -> None:
    assert login.user_from_cookie(login._fetch_cookie(current_cookie)) == (
        with_user[0],
        session_id,
        generate_auth_hash(with_user[0], session_id),
    )


def test_auth_cookie_is_valid_refuse_pre_16(pre_16_cookie: str) -> None:
    cookie = login._fetch_cookie(pre_16_cookie)
    assert login.auth_cookie_is_valid(cookie) is False


def test_auth_cookie_is_valid_refuse_pre_20(pre_20_cookie: str) -> None:
    cookie = login._fetch_cookie(pre_20_cookie)
    assert login.auth_cookie_is_valid(cookie) is False


def test_auth_cookie_is_valid_allow_current(current_cookie: str) -> None:
    cookie = login._fetch_cookie(current_cookie)
    assert login.auth_cookie_is_valid(cookie) is True


def test_web_server_auth_session(user_id: UserId) -> None:
    environ = dict(create_environ(), REMOTE_USER=str(user_id))

    with application_and_request_context(environ):
        assert user.id is None
        with login.authenticate(request) as authenticated:
            assert authenticated is True
            assert user.id == user_id
            assert active_user_session.user_id == user.id
        assert user.id is None


def test_ignore_transaction_ids(
    request_context: Iterator[None],
    monkeypatch: pytest.MonkeyPatch,
    with_automation_user: tuple[UserId, str],
) -> None:
    user_id, password = with_automation_user
    request.set_var("_secret", password)
    request.set_var("_username", user_id)
    with login.authenticate(request):
        assert transactions._ignore_transids
    assert transactions._ignore_transids is False
