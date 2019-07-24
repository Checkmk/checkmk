#!/usr/bin/env python
# encoding: utf-8

import io
import time

from werkzeug.test import create_environ

import cmk.gui.http as http
from cmk.gui.globals import html


def test_http_request_allowed_vars():
    environ = dict(create_environ(method="POST",
                                  content_type="application/x-www-form-urlencoded",
                                  input_stream=io.BytesIO("asd=x&_Y21rYWRtaW4%3D=aaa")),
                   REQUEST_URI='')
    req = http.Request(environ)
    assert req.var("asd") == "x"
    assert req.var("_Y21rYWRtaW4=") == "aaa"


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

    html.get_unicode_input("varname", deflt="lol")
    html.get_integer_input("varname2")
    html.get_request(exclude_vars=["varname2"])
    # TODO: Make a test which works:
    # html.parse_field_storage(["field1", "field2"], handle_uploads_as_file_obj = False)


def test_response_set_http_cookie(register_builtin_html):
    html.response.set_http_cookie("auth_SITE", "user:123456:abcdefg")

    assert html.response.headers.getlist("Set-Cookie")[-1] == \
        "auth_SITE=user:123456:abcdefg; HttpOnly; Path=/"


def test_response_set_http_cookie_secure(register_builtin_html, monkeypatch):
    html.response.set_http_cookie("auth_SITE", "user:123456:abcdefg", secure=True)

    assert html.response.headers.getlist("Set-Cookie")[-1] == \
            "auth_SITE=user:123456:abcdefg; Secure; HttpOnly; Path=/"


def test_response_del_cookie(register_builtin_html, monkeypatch):
    monkeypatch.setattr(time, "time", lambda: 0)

    html.response.delete_cookie("auth_SITE")

    assert html.response.headers.getlist("Set-Cookie")[-1] == \
            "auth_SITE=; Expires=Thu, 01-Jan-1970 00:00:00 GMT; Max-Age=0; Path=/"


# User IDs in Check_MK may contain non ascii characters. When they need to be encoded,
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
        "xyz=123; auth_stable=lärs:1534272374.61:1f59cac3fcd5bcc389e4f8397bed315b; abc=123")
    request = http.Request(environ)

    assert isinstance(request.cookie("auth_stable"), bytes)
    assert request.cookie("auth_stable") == "lärs:1534272374.61:1f59cac3fcd5bcc389e4f8397bed315b"

    assert request.has_cookie("xyz")
    assert request.has_cookie("abc")
