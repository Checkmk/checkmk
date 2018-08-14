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
            ("Set-Cookie", "auth_SITE=user:123456:abcdefg; HttpOnly; Path=/")


def test_response_set_cookie_secure(register_builtin_html, monkeypatch):
    # TODO: Find better way to directly patch the property html.request.is_ssl_request
    monkeypatch.setitem(html.request._wsgi_environ, "HTTP_X_FORWARDED_PROTO", "https")

    html.response.set_cookie("auth_SITE", "user:123456:abcdefg")

    assert html.response.headers[-1] == \
            ("Set-Cookie", "auth_SITE=user:123456:abcdefg; Secure; HttpOnly; Path=/")


def test_response_set_cookie_expires(register_builtin_html, monkeypatch):
    monkeypatch.setattr(time, "time", lambda: 0)

    html.response.set_cookie("auth_SITE", "user:123456:abcdefg", expires=60)

    assert html.response.headers[-1] == \
            ("Set-Cookie", "auth_SITE=user:123456:abcdefg; Expires=Thu, 01-Jan-1970 00:01:00 GMT; HttpOnly; Path=/")


def test_response_del_cookie(register_builtin_html, monkeypatch):
    monkeypatch.setattr(time, "time", lambda: 0)

    html.response.del_cookie("auth_SITE")

    assert html.response.headers[-1] == \
            ("Set-Cookie", "auth_SITE=; Expires=Wed, 31-Dec-1969 23:59:00 GMT; HttpOnly; Path=/")


# User IDs in Check_MK may contain non ascii characters. When they need to be encoded,
# they are encoded in UTF-8. Since this is possible the user names in the cookies directly
# contain those UTF-8 encoded user names.
# Until we decide that distributed setups between the current version and the previous
# versions are not possible anymore we need to be able to deal with the old cookie format.
#
# We dropped the old format during 1.6 development. It would be a good time to drop the
# compatibility with the old format earliest with 1.7.
def test_pre_16_format_cookie_handling(monkeypatch):
    wsgi_environ = {
        # This is no complete WSGI environment. But we currently don't need more.
        "wsgi.input"  : "",
        "SCRIPT_NAME" : "",
        "HTTP_COOKIE" : "xyz=123; auth_stable=lärs:1534272374.61:1f59cac3fcd5bcc389e4f8397bed315b; abc=123"
    }

    request = http.Request(wsgi_environ)

    assert isinstance(request.cookie("auth_stable"), bytes)
    assert request.cookie("auth_stable") == "lärs:1534272374.61:1f59cac3fcd5bcc389e4f8397bed315b"

    assert request.has_cookie("xyz")
    assert request.has_cookie("abc")
