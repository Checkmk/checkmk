#!/usr/bin/env python
# encoding: utf-8

import time

import cmk.gui.http as http
from cmk.gui.globals import html


def test_cookie_handling(register_builtin_html, monkeypatch):
    monkeypatch.setattr(html.request, "cookies", {"cookie1": {"key": "1a"}})
    assert html.request.get_cookie_names() == ["cookie1"]
    assert html.request.has_cookie("cookie1")
    assert not html.request.has_cookie("cookie2")
    #TODO: Write proper test assert html.cookie("cookie1", "2n class") == "1a"
    assert html.request.cookie("cookie2", "2n class") == "2n class"


# TODO: Write valid test
def test_request_processing(register_builtin_html):
    html.add_var("varname", "1a")
    html.add_var("varname2", 1)

    html.get_unicode_input("varname", deflt = "lol")
    html.get_integer_input("varname2")
    html.get_request(exclude_vars=["varname2"])
    # TODO: Make a test which works:
    # html.parse_field_storage(["field1", "field2"], handle_uploads_as_file_obj = False)


def test_response_set_cookie(register_builtin_html):
    html.response.set_cookie("auth_SITE", "user:123456:abcdefg")

    assert html.response.headers[-1] == \
            ("Set-Cookie", "auth_SITE=user:123456:abcdefg; httponly; Path=/")


def test_response_set_cookie_secure(register_builtin_html, monkeypatch):
    # TODO: Find better way to directly patch the property html.request.is_ssl_request
    monkeypatch.setitem(html.request._wsgi_environ, "HTTP_X_FORWARDED_PROTO", "https")

    html.response.set_cookie("auth_SITE", "user:123456:abcdefg")

    assert html.response.headers[-1] == \
            ("Set-Cookie", "auth_SITE=user:123456:abcdefg; httponly; Path=/; secure")


def test_response_set_cookie_expires(register_builtin_html, monkeypatch):
    monkeypatch.setattr(time, "time", lambda: 0)

    html.response.set_cookie("auth_SITE", "user:123456:abcdefg", expires=60)

    assert html.response.headers[-1] == \
            ("Set-Cookie", "auth_SITE=user:123456:abcdefg; expires=Thu, 01 Jan 1970 00:01:00 GMT; httponly; Path=/")


def test_response_del_cookie(register_builtin_html, monkeypatch):
    monkeypatch.setattr(time, "time", lambda: 0)

    html.response.del_cookie("auth_SITE")

    assert html.response.headers[-1] == \
            ("Set-Cookie", "auth_SITE=; expires=Wed, 31 Dec 1969 23:59:00 GMT; httponly; Path=/")
