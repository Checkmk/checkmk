#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import io
import time
from collections.abc import Iterator
from contextlib import nullcontext

import pytest
from pydantic import BaseModel
from pytest import MonkeyPatch
from werkzeug.exceptions import RequestEntityTooLarge
from werkzeug.test import create_environ

from tests.unit.cmk.web_test_app import WebTestAppForCMK

from cmk.gui import http
from cmk.gui.exceptions import MKUserError
from cmk.gui.http import ContentDispositionType, request, response
from cmk.gui.utils.script_helpers import application_and_request_context

global_request = request
MAX_FORM_SIZE = 20  # MBs, as seen in cmk.gui.http::Request.max_form_memory_size

RequestContextFixture = Iterator[None]


def test_request_del_vars_from_query_string() -> None:
    r = http.Request(
        create_environ(
            method="GET",
            query_string="a=1&b=2",
        )
    )
    r.del_var_from_env("a")
    assert r.query_string == b"b=2"


def test_request_del_vars_from_post_body() -> None:
    r = http.Request(
        create_environ(
            method="GET",
            query_string="a=1&b=2",
            content_type="application/x-www-form-urlencoded",
            input_stream=io.BytesIO(b"a=2&c=3"),
        )
    )
    r.del_var_from_env("a")
    assert len(r.form) == 1
    assert r.query_string == b"b=2"


def test_http_request_allowed_vars() -> None:
    environ = dict(
        create_environ(
            method="POST",
            content_type="application/x-www-form-urlencoded",
            input_stream=io.BytesIO(b"asd=x&_Y21rYWRtaW4%3D=aaa&foo%3ABAR_BAZ=abc"),
        ),
        REQUEST_URI="",
    )
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
def set_vars(request_context: RequestContextFixture) -> None:
    request.set_var("xyz", "x")
    request.set_var("abc", "äbc")


@pytest.fixture()
def set_int_vars(request_context: RequestContextFixture) -> None:
    request.set_var("number", "2")
    request.set_var("float", "2.2")
    request.set_var("not_a_number", "a")


@pytest.mark.usefixtures("set_vars")
def test_get_str_input_type() -> None:
    assert request.get_str_input("xyz") == "x"
    assert isinstance(request.get_str_input("xyz"), str)


@pytest.mark.usefixtures("set_vars")
def test_get_str_input_non_ascii() -> None:
    assert request.get_str_input("abc") == "äbc"


@pytest.mark.usefixtures("set_vars")
def test_get_str_input_default() -> None:
    assert request.get_str_input("get_default", "xyz") == "xyz"
    assert request.get_str_input("zzz") is None


@pytest.mark.usefixtures("set_vars")
def test_get_str_input_mandatory_input_type() -> None:
    assert request.get_str_input_mandatory("xyz") == "x"
    assert isinstance(request.get_str_input_mandatory("xyz"), str)


@pytest.mark.usefixtures("set_vars")
def test_get_str_input_mandatory_non_ascii() -> None:
    assert request.get_str_input_mandatory("abc") == "äbc"


@pytest.mark.usefixtures("set_vars")
def test_get_str_input_mandatory_default() -> None:
    assert request.get_str_input_mandatory("get_default", "xyz") == "xyz"

    with pytest.raises(MKUserError, match="is missing"):
        request.get_str_input_mandatory("zzz")


@pytest.mark.usefixtures("set_vars")
def test_get_binary_input_type() -> None:
    assert request.get_binary_input("xyz") == b"x"
    assert isinstance(request.get_str_input("xyz"), str)


@pytest.mark.usefixtures("set_vars")
def test_get_binary_input_non_ascii() -> None:
    assert request.get_binary_input("abc") == "äbc".encode()


@pytest.mark.usefixtures("set_vars")
def test_get_binary_input_default() -> None:
    assert request.get_binary_input("get_default", b"xyz") == b"xyz"
    assert request.get_binary_input("zzz") is None


@pytest.mark.usefixtures("set_vars")
def test_get_binary_input_mandatory_input_type() -> None:
    assert request.get_binary_input_mandatory("xyz") == b"x"
    assert isinstance(request.get_binary_input_mandatory("xyz"), bytes)


@pytest.mark.usefixtures("set_vars")
def test_get_binary_input_mandatory_non_ascii() -> None:
    assert request.get_binary_input_mandatory("abc") == "äbc".encode()


@pytest.mark.usefixtures("set_vars")
def test_get_binary_input_mandatory_default() -> None:
    assert request.get_binary_input_mandatory("get_default", b"xyz") == b"xyz"

    with pytest.raises(MKUserError, match="is missing"):
        request.get_binary_input_mandatory("zzz")


@pytest.mark.usefixtures("set_vars")
def test_get_ascii_input_input_type() -> None:
    assert request.get_ascii_input("xyz") == "x"
    assert isinstance(request.get_ascii_input("xyz"), str)


@pytest.mark.usefixtures("set_vars")
def test_get_ascii_input_non_ascii() -> None:
    with pytest.raises(MKUserError) as e:
        request.get_ascii_input("abc")
    assert "must only contain ASCII" in "%s" % e


@pytest.mark.usefixtures("set_vars")
def test_get_ascii_input_default() -> None:
    assert request.get_ascii_input("get_default", "xyz") == "xyz"
    assert request.get_ascii_input("zzz") is None


@pytest.mark.usefixtures("set_vars")
def test_get_ascii_input_mandatory_input_type() -> None:
    assert request.get_ascii_input_mandatory("xyz") == "x"
    assert isinstance(request.get_ascii_input_mandatory("xyz"), str)


@pytest.mark.usefixtures("set_vars")
def test_get_ascii_input_mandatory_non_ascii() -> None:
    with pytest.raises(MKUserError) as e:
        request.get_ascii_input_mandatory("abc")
    assert "must only contain ASCII" in "%s" % e


@pytest.mark.usefixtures("set_vars")
def test_get_ascii_input_mandatory_default() -> None:
    assert request.get_ascii_input_mandatory("get_default", "xyz") == "xyz"

    with pytest.raises(MKUserError, match="is missing"):
        request.get_ascii_input_mandatory("zzz")


@pytest.mark.usefixtures("set_int_vars")
def test_get_integer_input_default() -> None:
    assert request.get_integer_input("not_existing") is None
    assert request.get_integer_input("get_default", 1) == 1
    assert request.get_integer_input("bla") is None


@pytest.mark.usefixtures("set_int_vars")
def test_get_integer_input_regular() -> None:
    assert request.get_integer_input("number") == 2


@pytest.mark.usefixtures("set_int_vars")
def test_get_integer_input_float() -> None:
    with pytest.raises(MKUserError) as e:
        request.get_integer_input("float")
    assert "is not an integer" in "%s" % e


@pytest.mark.usefixtures("set_int_vars")
def test_get_integer_input_not_a_number() -> None:
    with pytest.raises(MKUserError) as e:
        request.get_integer_input("not_a_number")
    assert "is not an integer" in "%s" % e


@pytest.mark.usefixtures("set_int_vars")
def test_get_integer_input_mandatory_default() -> None:
    with pytest.raises(MKUserError) as e:
        request.get_integer_input_mandatory("not_existing")
    assert "is missing" in "%s" % e

    assert request.get_integer_input_mandatory("get_default", 1) == 1

    with pytest.raises(MKUserError) as e:
        request.get_integer_input_mandatory("bla")
    assert "is missing" in "%s" % e


@pytest.mark.usefixtures("set_int_vars")
def test_get_integer_input_mandatory_regular() -> None:
    assert request.get_integer_input_mandatory("number") == 2


@pytest.mark.usefixtures("set_int_vars")
def test_get_integer_input_mandatory_float() -> None:
    with pytest.raises(MKUserError) as e:
        request.get_integer_input_mandatory("float")
    assert "is not an integer" in "%s" % e


@pytest.mark.usefixtures("set_int_vars")
def test_get_integer_input_mandatory_not_a_number() -> None:
    with pytest.raises(MKUserError) as e:
        request.get_integer_input_mandatory("not_a_number")
    assert "is not an integer" in "%s" % e


class ModelForTest(BaseModel):
    my_float: float
    my_string: str


@pytest.mark.usefixtures("request_context")
def test_get_model_mandatory() -> None:
    request.set_var("my_model", '{"my_float": 23.42, "my_string": "yes"}')

    with pytest.raises(MKUserError):
        request.get_model_mandatory(ModelForTest, "Not existing")

    assert request.get_model_mandatory(ModelForTest, "my_model") == ModelForTest(
        my_float=23.42, my_string="yes"
    )


@pytest.mark.usefixtures("request_context")
def test_get_model_mandatory_invalid() -> None:
    request.set_var("my_model", '{"my_float": "mööp", "my_string": 17}')

    with pytest.raises(MKUserError):
        request.get_model_mandatory(ModelForTest, "my_model")


@pytest.mark.usefixtures("set_int_vars")
def test_get_validated_type_input() -> None:
    with pytest.raises(MKUserError) as e:
        request.get_validated_type_input(int, "not_a_number")
    assert "The value is not valid: " in str(e)

    assert request.get_validated_type_input(int, "Not existing", deflt=0) == 0

    assert request.get_validated_type_input(int, "Not existing") is None
    assert request.get_validated_type_input(int, "number") == 2
    assert request.get_validated_type_input(str, "number") == "2"


@pytest.mark.usefixtures("set_int_vars")
def test_get_validated_type_input_mandatory() -> None:
    with pytest.raises(MKUserError) as e:
        request.get_validated_type_input_mandatory(int, "Not existing")
    assert 'The parameter "Not existing" is missing.' in str(e)

    assert request.get_validated_type_input_mandatory(int, "Not existing", deflt=0) == 0


@pytest.mark.usefixtures("request_context")
def test_cookie_handling(monkeypatch: MonkeyPatch) -> None:
    with monkeypatch.context() as m:
        m.setattr(request, "cookies", {"cookie1": {"key": "1a"}})
        assert request.has_cookie("cookie1")
        assert not request.has_cookie("cookie2")
        # TODO: Write proper test assert html.cookie("cookie1", "2n class") == "1a"
        assert request.cookie("cookie2", "2n class") == "2n class"


# TODO: Write valid test
@pytest.mark.usefixtures("request_context")
def test_request_processing() -> None:
    global_request.set_var("varname", "1a")
    global_request.set_var("varname2", "1")

    global_request.get_str_input("varname", deflt="lol")
    global_request.get_integer_input_mandatory("varname2")
    global_request.get_request(exclude_vars=["varname2"])
    # TODO: Make a test which works:
    # html.parse_field_storage(["field1", "field2"], handle_uploads_as_file_obj = False)


# Needs to be equal
COOKIE_PATH = "/NO_SITE/"


@pytest.mark.usefixtures("request_context")
def test_response_set_http_cookie() -> None:
    response.set_http_cookie("auth_SITE", "user:123456:abcdefg", secure=False)

    assert (
        response.headers.getlist("Set-Cookie")[-1]
        == f"auth_SITE=user:123456:abcdefg; HttpOnly; Path={COOKIE_PATH}; SameSite=Lax"
    )


@pytest.mark.usefixtures("request_context")
def test_response_set_http_cookie_secure() -> None:
    response.set_http_cookie("auth_SITE", "user:123456:abcdefg", secure=True)

    assert (
        response.headers.getlist("Set-Cookie")[-1]
        == f"auth_SITE=user:123456:abcdefg; Secure; HttpOnly; Path={COOKIE_PATH}; SameSite=Lax"
    )


@pytest.mark.usefixtures("request_context")
def test_response_del_cookie(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(time, "time", lambda: 0)

    response.unset_http_cookie("auth_SITE")

    assert (
        response.headers.getlist("Set-Cookie")[-1]
        == f"auth_SITE=; Expires=Thu, 01 Jan 1970 00:00:00 GMT; Max-Age=0; Path={COOKIE_PATH}"
    )


@pytest.mark.parametrize(
    ["size_mb", "error"],
    [
        pytest.param(1024 * 1024 * (MAX_FORM_SIZE - 1), False, id="under_limit"),
        pytest.param(1024 * 1024 * MAX_FORM_SIZE, True, id="at_limit"),
        pytest.param(1024 * 1024 * (MAX_FORM_SIZE * 10), True, id="over_limit"),
    ],
)
def test_response_413_form_size_limit(
    wsgi_app: WebTestAppForCMK,
    patch_theme: None,
    size_mb: int,
    error: bool,
) -> None:
    """Validate the maximum form size remains under 20MB.

    Args:
        wsgi_app (WebTestAppForCMK): wsgi client of the flask application.
        patch_theme (None): patch frontend configuration for unit testing.
        size_mb (int): size of data added to the form.
        error (bool): whether an error is raised or not.
    """
    content = "a" * size_mb
    with pytest.raises(RequestEntityTooLarge) if error else nullcontext():
        wsgi_app.post(
            "/NO_SITE/check_mk/login.py",
            data={"_username": content},
        )


# User IDs in Checkmk may contain non ascii characters. When they need to be encoded,
# they are encoded in UTF-8. Since this is possible the user names in the cookies directly
# contain those UTF-8 encoded user names.
# Until we decide that distributed setups between the current version and the previous
# versions are not possible anymore we need to be able to deal with the old cookie format.
#
# We dropped the old format during 1.6 development. It would be a good time to drop the
# compatibility with the old format earliest with 1.7.
def test_pre_16_format_cookie_handling() -> None:
    environ = dict(
        create_environ(),
        HTTP_COOKIE="xyz=123; auth_stable=lärs:1534272374.61:1f59cac3fcd5bcc389e4f8397bed315b; abc=123",
    )
    _request = http.Request(environ)

    assert isinstance(_request.cookie("auth_stable"), str)
    assert _request.cookie("auth_stable") == "lärs:1534272374.61:1f59cac3fcd5bcc389e4f8397bed315b"

    assert _request.has_cookie("xyz")
    assert _request.has_cookie("abc")


def test_del_vars_from_post() -> None:
    environ = create_environ(
        input_stream=io.BytesIO(b"_username=foo&_secret=bar"),
        content_type="application/x-www-form-urlencoded",
    )
    with application_and_request_context(environ):
        assert global_request.form

        global_request.del_var_from_env("_username")
        global_request.del_var_from_env("_secret")

        assert not global_request.form


def test_del_vars_from_env() -> None:
    environ = create_environ(
        query_string="foo=foo&_username=foo&_password=bar&bar=bar",
    )
    with application_and_request_context(environ):
        # First we hit the cached property, so we can see that the underlying Request object
        # actually got replaced later.
        _ = global_request.args
        _ = request.args

        assert request.query_string

        request.set_var("foo", "123")

        request.del_var_from_env("_username")
        request.del_var_from_env("_password")

        # Make test independent of dict sorting
        assert request.query_string in [b"foo=foo&bar=bar", b"bar=bar&foo=foo"]

        assert "_password" not in request.args
        assert "_username" not in request.args

        # Check the request local proxied version too.
        # Make test independent of dict sorting
        assert global_request.query_string in [b"foo=foo&bar=bar", b"bar=bar&foo=foo"]
        assert "_password" not in global_request.args
        assert "_username" not in global_request.args

        assert request.var("foo") == "123"


def test_del_vars() -> None:
    environ = create_environ(
        query_string="opt_x=x&foo=foo",
    )
    with application_and_request_context(environ):
        assert request.var("opt_x") == "x"
        assert request.var("foo") == "foo"

        request.del_vars(prefix="opt_")

        assert request.var("opt_x") is None
        assert request.var("foo") == "foo"

        # Check the request local proxied version too
        assert global_request.var("opt_x") is None
        assert global_request.var("foo") == "foo"


@pytest.mark.parametrize("invalid_url", ["http://localhost/", "localhost:80/bla"])
@pytest.mark.usefixtures("request_context")
def test_get_url_input_invalid_urls(invalid_url: str) -> None:
    request.set_var("varname", invalid_url)

    with pytest.raises(MKUserError) as e:
        global_request.get_url_input("varname")
    assert "not a valid URL" in "%s" % e


@pytest.mark.usefixtures("request_context")
def test_get_url_input() -> None:
    global_request.set_var("url", "view.py?bla=blub")
    global_request.set_var("no_url", "2")
    global_request.set_var("invalid_url", "http://bla/")

    with pytest.raises(MKUserError) as e:
        global_request.get_url_input("not_existing")
    assert "is missing" in "%s" % e

    assert global_request.get_url_input("get_default", "my_url.py") == "my_url.py"
    assert global_request.get_url_input("get_default", "http://bla/") == "http://bla/"
    assert global_request.get_url_input("url") == "view.py?bla=blub"
    assert global_request.get_url_input("no_url") == "2"

    with pytest.raises(MKUserError) as e:
        global_request.get_url_input("invalid_url")
    assert "not a valid" in "%s" % e

    assert global_request.get_url_input("no_url") == "2"


# Test that content types will correctly be handled for content disposition


@pytest.mark.parametrize(
    "content_type, disposition_type, file_name",
    [
        (
            "application/x-mkp",
            ContentDispositionType.INLINE,
            "file.mkp",
        ),
        (
            "text/csv",
            ContentDispositionType.ATTACHMENT,
            "file.csv",
        ),
        (
            "image/png",
            ContentDispositionType.ATTACHMENT,
            "file.png",
        ),
        (
            "application/x-tgz",
            ContentDispositionType.ATTACHMENT,
            "file.tar.gz",
        ),
    ],
)
def test_content_disposition_valid(
    content_type: str,
    disposition_type: ContentDispositionType,
    file_name: str,
    request_context: None,
) -> None:
    response.set_content_type(content_type)
    response.set_content_disposition(disposition_type, file_name)


@pytest.mark.parametrize(
    "content_type, disposition_type, file_name",
    [
        (
            "application/x-mkp",
            ContentDispositionType.INLINE,
            "file.mkz",
        ),
        (
            "application/x-mkz",
            ContentDispositionType.INLINE,
            "file.mkp",
        ),
    ],
)
def test_content_disposition_invalid_extension(
    content_type: str,
    disposition_type: ContentDispositionType,
    file_name: str,
    request_context: None,
) -> None:
    response.set_content_type(content_type)
    with pytest.raises(
        ValueError, match="Invalid file extension: Have you set the Content-Type header?"
    ):
        response.set_content_disposition(disposition_type, file_name)


@pytest.mark.parametrize(
    "content_type, disposition_type, file_name",
    [
        (
            "application/x-mkp",
            ContentDispositionType.INLINE,
            "\\file.mkp",
        ),
        (
            "application/x-mkp",
            ContentDispositionType.INLINE,
            '"file.mkp',
        ),
    ],
)
def test_content_disposition_invalid_characters(
    content_type: str,
    disposition_type: ContentDispositionType,
    file_name: str,
    request_context: None,
) -> None:
    response.set_content_type(content_type)
    with pytest.raises(ValueError, match="Invalid character in filename"):
        response.set_content_disposition(disposition_type, file_name)


def test_remote_ip() -> None:
    r = http.Request(create_environ())
    assert r.remote_ip is None

    r = http.Request(
        create_environ(environ_base={"REMOTE_ADDR": "42.42.42.42"}),
    )
    assert r.remote_addr == "42.42.42.42"
    assert r.remote_ip == "42.42.42.42"

    r = http.Request(
        create_environ(
            environ_base={"REMOTE_ADDR": "42.42.42.42", "HTTP_X_FORWARDED_FOR": "23.23.23.23"}
        ),
    )
    assert r.remote_addr == "42.42.42.42"
    assert r.remote_ip == "42.42.42.42"

    r = http.Request(
        create_environ(environ_base={"REMOTE_ADDR": "::1", "HTTP_X_FORWARDED_FOR": "23.23.23.23"}),
    )
    assert r.remote_addr == "::1"
    assert r.remote_ip == "23.23.23.23"

    r = http.Request(
        create_environ(
            environ_base={"REMOTE_ADDR": "::1", "HTTP_X_FORWARDED_FOR": "42.42.42.42, 23.23.23.23"}
        ),
    )
    assert r.remote_addr == "::1"
    assert r.remote_ip == "23.23.23.23"
