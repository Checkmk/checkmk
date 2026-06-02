#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from scripts.html_validation.lib.exceptions import AuthMissingError
from scripts.html_validation.lib.http import build_auth_cookies, ResponseInfo


class TestBuildAuthCookies:
    def test_raises_when_credentials_missing(self) -> None:
        with pytest.raises(AuthMissingError):
            build_auth_cookies("", "", no_auth=False)

    def test_raises_when_key_missing(self) -> None:
        with pytest.raises(AuthMissingError):
            build_auth_cookies("", "some_val", no_auth=False)

    def test_raises_when_val_missing(self) -> None:
        with pytest.raises(AuthMissingError):
            build_auth_cookies("some_key", "", no_auth=False)

    def test_returns_none_when_no_auth(self) -> None:
        assert build_auth_cookies("", "", no_auth=True) is None

    def test_returns_cookie_dict(self) -> None:
        value = build_auth_cookies("auth_v260", "cmkadmin:abc", no_auth=False)
        expected = {"auth_v260": "cmkadmin:abc"}
        assert value == expected


class TestResponseInfoIsRedirectToLogin:
    def test_true_when_location_contains_login_py(self) -> None:
        info = _make_response_info(redirect_location="/v260/check_mk/login.py")
        assert info.is_redirect_to_login is True

    def test_false_when_location_is_empty(self) -> None:
        info = _make_response_info(redirect_location="")
        assert info.is_redirect_to_login is False

    def test_false_when_location_is_other_page(self) -> None:
        info = _make_response_info(redirect_location="/v260/check_mk/dashboard.py")
        assert info.is_redirect_to_login is False


class TestResponseInfoIsHtmlDocument:
    def test_true_for_html_content_type(self) -> None:
        info = _make_response_info(content_type="text/html; charset=utf-8")
        assert info.is_html_document is True

    def test_false_for_json_content_type(self) -> None:
        info = _make_response_info(content_type="application/json")
        assert info.is_html_document is False

    def test_false_for_empty_content_type(self) -> None:
        info = _make_response_info(content_type="")
        assert info.is_html_document is False


def _make_response_info(**kwargs: str | int) -> ResponseInfo:
    defaults: dict[str, str | int] = {
        "url": "http://localhost/check_mk/dashboard.py",
        "status_code": 200,
        "content_type": "text/html; charset=utf-8",
        "redirect_location": "",
    }
    return ResponseInfo(**{**defaults, **kwargs})  # type: ignore[arg-type]
