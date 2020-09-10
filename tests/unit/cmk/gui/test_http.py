#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import io
import time

import pytest  # type: ignore[import]

from werkzeug.test import create_environ

import cmk.gui.http as http
from cmk.gui.globals import html
from cmk.gui.exceptions import MKUserError


def test_http_request_allowed_vars():
    environ = dict(create_environ(
        method="POST",
        content_type="application/x-www-form-urlencoded",
        input_stream=io.BytesIO(b"asd=x&_Y21rYWRtaW4%3D=aaa&foo%3ABAR_BAZ=abc")),
                   REQUEST_URI='')
    req = http.Request(environ)
    assert req.var("asd") == "x"
    assert req.var("_Y21rYWRtaW4=") == "aaa"
    assert req.var("foo:BAR_BAZ") == "abc"
    assert req.var("foo:BAR_BAZ", "default") == "abc"

    assert req.var("not_present") is None
    assert req.var("not_present", "default") == "default"

    req.set_var("test", "foo")
    assert req.var("test") == "foo"
    req.del_var("test")
    assert req.var("test") is None
    assert req.var("test", "default") == "default"


@pytest.fixture()
def set_vars(register_builtin_html):
    html.request.set_var("xyz", "x")
    html.request.set_var("abc", "äbc")


@pytest.fixture()
def set_int_vars(register_builtin_html):
    html.request.set_var("number", "2")
    html.request.set_var("float", "2.2")
    html.request.set_var("not_a_number", "a")


@pytest.mark.usefixtures("set_vars")
def test_get_str_input_type():
    assert html.request.get_str_input("xyz") == "x"
    assert isinstance(html.request.get_str_input("xyz"), str)


@pytest.mark.usefixtures("set_vars")
def test_get_str_input_non_ascii():
    assert html.request.get_str_input("abc") == "äbc"


@pytest.mark.usefixtures("set_vars")
def test_get_str_input_default():
    assert html.request.get_str_input("get_default", "xyz") == "xyz"
    assert html.request.get_str_input("zzz") is None


@pytest.mark.usefixtures("set_vars")
def test_get_str_input_mandatory_input_type():
    assert html.request.get_str_input_mandatory("xyz") == "x"
    assert isinstance(html.request.get_str_input_mandatory("xyz"), str)


@pytest.mark.usefixtures("set_vars")
def test_get_str_input_mandatory_non_ascii():
    assert html.request.get_str_input_mandatory("abc") == "äbc"


@pytest.mark.usefixtures("set_vars")
def test_get_str_input_mandatory_default():
    assert html.request.get_str_input_mandatory("get_default", "xyz") == "xyz"

    with pytest.raises(MKUserError, match="is missing"):
        html.request.get_str_input_mandatory("zzz")


@pytest.mark.usefixtures("set_vars")
def test_get_binary_input_type():
    assert html.request.get_binary_input("xyz") == b"x"
    assert isinstance(html.request.get_str_input("xyz"), str)


@pytest.mark.usefixtures("set_vars")
def test_get_binary_input_non_ascii():
    assert html.request.get_binary_input("abc") == u"äbc".encode("utf-8")


@pytest.mark.usefixtures("set_vars")
def test_get_binary_input_default():
    assert html.request.get_binary_input("get_default", b"xyz") == b"xyz"
    assert html.request.get_binary_input("zzz") is None


@pytest.mark.usefixtures("set_vars")
def test_get_binary_input_mandatory_input_type():
    assert html.request.get_binary_input_mandatory("xyz") == b"x"
    assert isinstance(html.request.get_binary_input_mandatory("xyz"), bytes)


@pytest.mark.usefixtures("set_vars")
def test_get_binary_input_mandatory_non_ascii():
    assert html.request.get_binary_input_mandatory("abc") == u"äbc".encode("utf-8")


@pytest.mark.usefixtures("set_vars")
def test_get_binary_input_mandatory_default():
    assert html.request.get_binary_input_mandatory("get_default", b"xyz") == b"xyz"

    with pytest.raises(MKUserError, match="is missing"):
        html.request.get_binary_input_mandatory("zzz")


@pytest.mark.usefixtures("set_vars")
def test_get_ascii_input_input_type():
    assert html.request.get_ascii_input("xyz") == "x"
    assert isinstance(html.request.get_ascii_input("xyz"), str)


@pytest.mark.usefixtures("set_vars")
def test_get_ascii_input_non_ascii():
    with pytest.raises(MKUserError) as e:
        html.request.get_ascii_input("abc")
    assert "must only contain ASCII" in "%s" % e


@pytest.mark.usefixtures("set_vars")
def test_get_ascii_input_default():
    assert html.request.get_ascii_input("get_default", "xyz") == "xyz"
    assert html.request.get_ascii_input("zzz") is None


@pytest.mark.usefixtures("set_vars")
def test_get_ascii_input_mandatory_input_type():
    assert html.request.get_ascii_input_mandatory("xyz") == "x"
    assert isinstance(html.request.get_ascii_input_mandatory("xyz"), str)


@pytest.mark.usefixtures("set_vars")
def test_get_ascii_input_mandatory_non_ascii():
    with pytest.raises(MKUserError) as e:
        html.request.get_ascii_input_mandatory("abc")
    assert "must only contain ASCII" in "%s" % e


@pytest.mark.usefixtures("set_vars")
def test_get_ascii_input_mandatory_default():
    assert html.request.get_ascii_input_mandatory("get_default", "xyz") == "xyz"

    with pytest.raises(MKUserError, match="is missing"):
        html.request.get_ascii_input_mandatory("zzz")


@pytest.mark.usefixtures("set_vars")
def test_get_unicode_input_type():
    assert html.request.get_unicode_input("xyz") == "x"
    assert isinstance(html.request.get_unicode_input("xyz"), str)


@pytest.mark.usefixtures("set_vars")
def test_get_unicode_input_non_ascii():
    assert html.request.get_unicode_input("abc") == u"äbc"


@pytest.mark.usefixtures("set_vars")
def test_get_unicode_input_default():
    assert html.request.get_unicode_input("get_default", u"xyz") == u"xyz"
    assert html.request.get_unicode_input("zzz") is None


@pytest.mark.usefixtures("set_vars")
def test_get_unicode_input_mandatory_input_type():
    assert html.request.get_unicode_input_mandatory("xyz") == u"x"
    assert isinstance(html.request.get_unicode_input_mandatory("xyz"), str)


@pytest.mark.usefixtures("set_vars")
def test_get_unicode_input_mandatory_non_ascii():
    assert html.request.get_unicode_input_mandatory("abc") == u"äbc"


@pytest.mark.usefixtures("set_vars")
def test_get_unicode_input_mandatory_default():
    assert html.request.get_unicode_input_mandatory("get_default", u"xyz") == u"xyz"

    with pytest.raises(MKUserError, match="is missing"):
        html.request.get_unicode_input_mandatory("zzz")


@pytest.mark.usefixtures("set_int_vars")
def test_get_integer_input_default():
    assert html.request.get_integer_input("not_existing") is None
    assert html.request.get_integer_input("get_default", 1) == 1
    assert html.request.get_integer_input("bla") is None


@pytest.mark.usefixtures("set_int_vars")
def test_get_integer_input_regular():
    assert html.request.get_integer_input("number") == 2


@pytest.mark.usefixtures("set_int_vars")
def test_get_integer_input_float():
    with pytest.raises(MKUserError) as e:
        html.request.get_integer_input("float")
    assert "is not an integer" in "%s" % e


@pytest.mark.usefixtures("set_int_vars")
def test_get_integer_input_not_a_number():
    with pytest.raises(MKUserError) as e:
        html.request.get_integer_input("not_a_number")
    assert "is not an integer" in "%s" % e


@pytest.mark.usefixtures("set_int_vars")
def test_get_integer_input_mandatory_default():
    with pytest.raises(MKUserError) as e:
        html.request.get_integer_input_mandatory("not_existing")
    assert "is missing" in "%s" % e

    assert html.request.get_integer_input_mandatory("get_default", 1) == 1

    with pytest.raises(MKUserError) as e:
        html.request.get_integer_input_mandatory("bla")
    assert "is missing" in "%s" % e


@pytest.mark.usefixtures("set_int_vars")
def test_get_integer_input_mandatory_regular():
    assert html.request.get_integer_input_mandatory("number") == 2


@pytest.mark.usefixtures("set_int_vars")
def test_get_integer_input_mandatory_float():
    with pytest.raises(MKUserError) as e:
        html.request.get_integer_input_mandatory("float")
    assert "is not an integer" in "%s" % e


@pytest.mark.usefixtures("set_int_vars")
def test_get_integer_input_mandatory_not_a_number():
    with pytest.raises(MKUserError) as e:
        html.request.get_integer_input_mandatory("not_a_number")
    assert "is not an integer" in "%s" % e


def test_cookie_handling(register_builtin_html, monkeypatch):
    monkeypatch.setattr(html.request, "cookies", {"cookie1": {"key": "1a"}})
    assert html.request.get_cookie_names() == ["cookie1"]
    assert html.request.has_cookie("cookie1")
    assert not html.request.has_cookie("cookie2")
    #TODO: Write proper test assert html.cookie("cookie1", "2n class") == "1a"
    assert html.request.cookie("cookie2", "2n class") == "2n class"


# TODO: Write valid test
def test_request_processing(register_builtin_html):
    html.request.set_var("varname", "1a")
    html.request.set_var("varname2", "1")

    html.request.get_unicode_input("varname", deflt="lol")
    html.request.get_integer_input_mandatory("varname2")
    html.get_request(exclude_vars=["varname2"])
    # TODO: Make a test which works:
    # html.parse_field_storage(["field1", "field2"], handle_uploads_as_file_obj = False)


def test_response_set_http_cookie(register_builtin_html):
    html.response.set_http_cookie("auth_SITE", "user:123456:abcdefg")

    assert html.response.headers.getlist("Set-Cookie")[-1] == \
        "auth_SITE=user:123456:abcdefg; HttpOnly; Path=/; SameSite=Lax"


def test_response_set_http_cookie_secure(register_builtin_html, monkeypatch):
    html.response.set_http_cookie("auth_SITE", "user:123456:abcdefg", secure=True)

    assert html.response.headers.getlist("Set-Cookie")[-1] == \
            "auth_SITE=user:123456:abcdefg; Secure; HttpOnly; Path=/; SameSite=Lax"


def test_response_del_cookie(register_builtin_html, monkeypatch):
    monkeypatch.setattr(time, "time", lambda: 0)

    html.response.delete_cookie("auth_SITE")

    assert html.response.headers.getlist("Set-Cookie")[-1] == \
            "auth_SITE=; Expires=Thu, 01-Jan-1970 00:00:00 GMT; Max-Age=0; Path=/"


# User IDs in Checkmk may contain non ascii characters. When they need to be encoded,
# they are encoded in UTF-8. Since this is possible the user names in the cookies directly
# contain those UTF-8 encoded user names.
# Until we decide that distributed setups between the current version and the previous
# versions are not possible anymore we need to be able to deal with the old cookie format.
#
# We dropped the old format during 1.6 development. It would be a good time to drop the
# compatibility with the old format earliest with 1.7.
def test_pre_16_format_cookie_handling(monkeypatch):
    environ = dict(
        create_environ(),
        HTTP_COOKIE=
        u"xyz=123; auth_stable=lärs:1534272374.61:1f59cac3fcd5bcc389e4f8397bed315b; abc=123".encode(
            "utf-8"))
    request = http.Request(environ)

    assert isinstance(request.cookie("auth_stable"), str)
    assert request.cookie("auth_stable") == "lärs:1534272374.61:1f59cac3fcd5bcc389e4f8397bed315b"

    assert request.has_cookie("xyz")
    assert request.has_cookie("abc")
