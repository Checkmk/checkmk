#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest
from werkzeug.test import create_environ

from testlib.utils import DummyApplication

from cmk.utils.type_defs import UserId

import cmk.gui.htmllib as htmllib
import cmk.gui.login as login
import cmk.gui.http as http
import cmk.gui.userdb as userdb
from cmk.gui.globals import AppContext, RequestContext
from cmk.gui.exceptions import MKAuthException


@pytest.fixture(name="pre_16_cookie")
def fixture_pre_16_cookie():
    environ = dict(
        create_environ(),
        HTTP_COOKIE=
        u"xyz=123; auth_stable=lärs:1534272374.61:1f59cac3fcd5bcc389e4f8397bed315b; abc=123".encode(
            "utf-8"))

    with AppContext(DummyApplication(environ, None)), \
            RequestContext(htmllib.html(http.Request(environ))):
        yield "auth_stable"


@pytest.fixture(name="pre_20_cookie")
def fixture_pre_20_cookie():
    environ = dict(
        create_environ(),
        HTTP_COOKIE=
        u"xyz=123; auth_stable=lärs:1534272374.61:1f59cac3fcd5bcc389e4f8397bed315b; abc=123".encode(
            "utf-8"))

    with AppContext(DummyApplication(environ, None)), \
            RequestContext(htmllib.html(http.Request(environ))):
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

    with AppContext(DummyApplication(environ, None)), \
            RequestContext(htmllib.html(http.Request(environ))):
        yield cookie_name


def test_parse_auth_cookie_refuse_pre_16(pre_16_cookie):
    with pytest.raises(MKAuthException, match="Refusing pre 2.0"):
        login._parse_auth_cookie(pre_16_cookie)


def test_parse_auth_cookie_refuse_pre_20(pre_20_cookie):
    with pytest.raises(MKAuthException, match="Refusing pre 2.0"):
        login._parse_auth_cookie(pre_20_cookie)


def test_parse_auth_cookie_allow_current(current_cookie, with_user, session_id):
    assert login._parse_auth_cookie(current_cookie) == (UserId(
        with_user[0]), session_id, login._generate_auth_hash(with_user[0], session_id))


def test_auth_cookie_is_valid_refuse_pre_16(pre_16_cookie):
    assert login._auth_cookie_is_valid(pre_16_cookie) is False


def test_auth_cookie_is_valid_refuse_pre_20(pre_20_cookie):
    assert login._auth_cookie_is_valid(pre_20_cookie) is False


def test_auth_cookie_is_valid_allow_current(current_cookie):
    assert login._auth_cookie_is_valid(current_cookie) is True
