#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest
from werkzeug.test import create_environ

from cmk.utils.type_defs import UserId

import cmk.gui.login as login
import cmk.gui.userdb as userdb
from cmk.gui.config import load_config
from cmk.gui.exceptions import MKAuthException
from cmk.gui.globals import request, session
from cmk.gui.utils.logged_in import user
from cmk.gui.utils.script_helpers import application_and_request_context


@pytest.fixture(name="user_id")
def fixture_user_id(with_user):
    return UserId(with_user[0])


def test_authenticate_success(request_context, monkeypatch, user_id):
    monkeypatch.setattr(login, "_check_auth", lambda r: user_id)
    assert user.id is None
    with login.authenticate(request) as authenticated:
        assert authenticated is True
        assert user.id == user_id
    assert user.id is None


def test_authenticate_fails(request_context, monkeypatch, user_id):
    monkeypatch.setattr(login, "_check_auth", lambda r: None)
    assert user.id is None
    with login.authenticate(request) as authenticated:
        assert authenticated is False
        assert user.id is None
    assert user.id is None


@pytest.fixture(name="pre_16_cookie")
def fixture_pre_16_cookie():
    environ = dict(
        create_environ(),
        HTTP_COOKIE="xyz=123; auth_stable=lärs:1534272374.61:1f59cac3fcd5bcc389e4f8397bed315b; abc=123".encode(
            "utf-8"
        ),
    )

    with application_and_request_context(environ):
        yield "auth_stable"


@pytest.fixture(name="pre_20_cookie")
def fixture_pre_20_cookie():
    environ = dict(
        create_environ(),
        HTTP_COOKIE="xyz=123; auth_stable=lärs:1534272374.61:1f59cac3fcd5bcc389e4f8397bed315b; abc=123".encode(
            "utf-8"
        ),
    )

    with application_and_request_context(environ):
        yield "auth_stable"


@pytest.fixture(name="session_id")
def fixture_session_id(with_user):
    user_id = with_user[0]
    return userdb._initialize_session(user_id)


@pytest.fixture(name="current_cookie")
def fixture_current_cookie(with_user, session_id):
    user_id = with_user[0]
    cookie_name = login.auth_cookie_name()
    cookie_value = login._auth_cookie_value(user_id, session_id)

    environ = dict(create_environ(), HTTP_COOKIE=f"{cookie_name}={cookie_value}".encode("utf-8"))

    with application_and_request_context(environ):
        load_config()
        yield cookie_name


def test_parse_auth_cookie_refuse_pre_16(pre_16_cookie):
    with pytest.raises(MKAuthException, match="Refusing pre 2.0"):
        login.user_from_cookie(login._fetch_cookie(pre_16_cookie))


def test_parse_auth_cookie_refuse_pre_20(pre_20_cookie):
    with pytest.raises(MKAuthException, match="Refusing pre 2.0"):
        login.user_from_cookie(login._fetch_cookie(pre_20_cookie))


def test_parse_auth_cookie_allow_current(current_cookie, with_user, session_id):
    assert login.user_from_cookie(login._fetch_cookie(current_cookie)) == (
        UserId(with_user[0]),
        session_id,
        login._generate_auth_hash(with_user[0], session_id),
    )


def test_auth_cookie_is_valid_refuse_pre_16(pre_16_cookie):
    cookie = login._fetch_cookie(pre_16_cookie)
    assert login.auth_cookie_is_valid(cookie) is False


def test_auth_cookie_is_valid_refuse_pre_20(pre_20_cookie):
    cookie = login._fetch_cookie(pre_20_cookie)
    assert login.auth_cookie_is_valid(cookie) is False


def test_auth_cookie_is_valid_allow_current(current_cookie):
    cookie = login._fetch_cookie(current_cookie)
    assert login.auth_cookie_is_valid(cookie) is True


def test_web_server_auth_session(user_id):
    environ = dict(create_environ(), REMOTE_USER=str(user_id))

    with application_and_request_context(environ):
        assert user.id is None
        with login.authenticate(request) as authenticated:
            assert authenticated is True
            assert user.id == user_id
            assert session.user_id == user.id
        assert user.id is None
