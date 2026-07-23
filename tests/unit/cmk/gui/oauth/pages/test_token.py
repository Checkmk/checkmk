#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import base64
import hashlib
import urllib.parse

import pytest
from flask import Flask
from pytest_mock import MockerFixture

from cmk.ccc.exceptions import MKTimeout
from cmk.gui.config import Config
from cmk.gui.http import request, response
from cmk.gui.oauth.pages._token import OAuthTokenPage
from cmk.gui.oauth.store._auth_code_store import AuthCodeRecord, AuthCodeStore
from cmk.gui.pages import PageContext
from cmk.utils.redis import disable_redis

_FORM_CONTENT_TYPE = "application/x-www-form-urlencoded"
# code_verifier is the RFC 7636 appendix B example value (43 characters);
# _stored_record() carries the matching S256 code_challenge.
_VALID_FORM = {
    "grant_type": "authorization_code",
    "code": "SplxlOBeZQQYbYS6WxSbIA",
    "client_id": "test-client",
    "code_verifier": "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk",
}


def _s256_challenge(code_verifier: str) -> str:
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def _stored_record(
    # The RFC 7636 appendix B challenge, matching _VALID_FORM's code_verifier.
    code_challenge: str = "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM",
    resource: str | None = "https://host/mysite/check_mk/mcp",
) -> AuthCodeRecord:
    return AuthCodeRecord(
        user_id="alice",
        client_id="test-client",
        redirect_uri="https://client.example/callback",
        scope="mcp",
        resource=resource,
        code_challenge=code_challenge,
    )


@pytest.mark.usefixtures("request_context")
class TestOAuthTokenPage:
    @pytest.mark.usefixtures("clean_redis")
    def test_redeems_a_stored_code_for_an_access_token(self, flask_app: Flask) -> None:
        AuthCodeStore().store(_VALID_FORM["code"], _stored_record())
        with flask_app.test_request_context(method="POST", data=_VALID_FORM):
            flask_app.preprocess_request()
            OAuthTokenPage(lambda: True).handle_page(PageContext(config=Config(), request=request))

            assert response.status_code == 200
            assert isinstance(response.json, dict)
            assert response.json["token_type"] == "Bearer"
            access_token = response.json["access_token"]
            assert isinstance(access_token, str)
            assert access_token

    @pytest.mark.usefixtures("clean_redis")
    def test_returns_a_different_access_token_for_each_code(self, flask_app: Flask) -> None:
        AuthCodeStore().store("first-code", _stored_record())
        AuthCodeStore().store("second-code", _stored_record())
        with flask_app.test_request_context(
            method="POST", data={**_VALID_FORM, "code": "first-code"}
        ):
            flask_app.preprocess_request()
            OAuthTokenPage(lambda: True).handle_page(PageContext(config=Config(), request=request))
            assert isinstance(response.json, dict)
            first_access_token = response.json["access_token"]

        with flask_app.test_request_context(
            method="POST", data={**_VALID_FORM, "code": "second-code"}
        ):
            flask_app.preprocess_request()
            OAuthTokenPage(lambda: True).handle_page(PageContext(config=Config(), request=request))
            assert isinstance(response.json, dict)
            second_access_token = response.json["access_token"]

        assert first_access_token != second_access_token

    def test_returns_404_when_disabled(self, flask_app: Flask) -> None:
        with flask_app.test_request_context(method="POST", data=_VALID_FORM):
            flask_app.preprocess_request()
            OAuthTokenPage(lambda: False).handle_page(PageContext(config=Config(), request=request))

            assert response.status_code == 404

    def test_returns_405_when_method_is_not_post(self, flask_app: Flask) -> None:
        with flask_app.test_request_context(method="GET"):
            flask_app.preprocess_request()
            OAuthTokenPage(lambda: True).handle_page(PageContext(config=Config(), request=request))

            assert response.status_code == 405

    def test_rejects_a_non_form_content_type(self, flask_app: Flask) -> None:
        with flask_app.test_request_context(
            method="POST",
            data='{"grant_type": "authorization_code"}',
            content_type="application/json",
        ):
            flask_app.preprocess_request()
            OAuthTokenPage(lambda: True).handle_page(PageContext(config=Config(), request=request))

            assert response.status_code == 400
            assert response.json == {"error": "invalid_request"}

    @pytest.mark.usefixtures("clean_redis")
    def test_accepts_a_form_content_type_with_charset_parameter(self, flask_app: Flask) -> None:
        AuthCodeStore().store(_VALID_FORM["code"], _stored_record())
        with flask_app.test_request_context(
            method="POST",
            data=urllib.parse.urlencode(_VALID_FORM),
            content_type="application/x-www-form-urlencoded; charset=UTF-8",
        ):
            flask_app.preprocess_request()
            OAuthTokenPage(lambda: True).handle_page(PageContext(config=Config(), request=request))

            assert response.status_code == 200

    def test_ignores_a_grant_type_in_the_query_string(self, flask_app: Flask) -> None:
        with flask_app.test_request_context(
            "/oauth_token.py?grant_type=authorization_code",
            method="POST",
            content_type=_FORM_CONTENT_TYPE,
        ):
            flask_app.preprocess_request()
            OAuthTokenPage(lambda: True).handle_page(PageContext(config=Config(), request=request))

            assert response.status_code == 400
            assert response.json == {"error": "invalid_request"}

    def test_rejects_a_missing_grant_type(self, flask_app: Flask) -> None:
        with flask_app.test_request_context(method="POST", content_type=_FORM_CONTENT_TYPE):
            flask_app.preprocess_request()
            OAuthTokenPage(lambda: True).handle_page(PageContext(config=Config(), request=request))

            assert response.status_code == 400
            assert response.json == {"error": "invalid_request"}

    def test_treats_an_empty_grant_type_as_missing(self, flask_app: Flask) -> None:
        with flask_app.test_request_context(method="POST", data={"grant_type": ""}):
            flask_app.preprocess_request()
            OAuthTokenPage(lambda: True).handle_page(PageContext(config=Config(), request=request))

            assert response.status_code == 400
            assert response.json == {"error": "invalid_request"}

    @pytest.mark.parametrize("grant_type", ["refresh_token", "client_credentials", "no-such-grant"])
    def test_rejects_unsupported_grant_types(self, flask_app: Flask, grant_type: str) -> None:
        with flask_app.test_request_context(method="POST", data={"grant_type": grant_type}):
            flask_app.preprocess_request()
            OAuthTokenPage(lambda: True).handle_page(PageContext(config=Config(), request=request))

            assert response.status_code == 400
            assert response.json == {"error": "unsupported_grant_type"}

    @pytest.mark.parametrize("param", ["code", "client_id", "code_verifier"])
    def test_rejects_a_missing_required_parameter(self, flask_app: Flask, param: str) -> None:
        form = {name: value for name, value in _VALID_FORM.items() if name != param}
        with flask_app.test_request_context(method="POST", data=form):
            flask_app.preprocess_request()
            OAuthTokenPage(lambda: True).handle_page(PageContext(config=Config(), request=request))

            assert response.status_code == 400
            assert response.json == {"error": "invalid_request"}

    @pytest.mark.parametrize("param", ["code", "client_id", "code_verifier"])
    def test_treats_an_empty_required_parameter_as_missing(
        self, flask_app: Flask, param: str
    ) -> None:
        with flask_app.test_request_context(method="POST", data={**_VALID_FORM, param: ""}):
            flask_app.preprocess_request()
            OAuthTokenPage(lambda: True).handle_page(PageContext(config=Config(), request=request))

            assert response.status_code == 400
            assert response.json == {"error": "invalid_request"}

    @pytest.mark.parametrize(
        "param", ["grant_type", "code", "client_id", "code_verifier", "redirect_uri", "resource"]
    )
    def test_rejects_a_duplicated_parameter(self, flask_app: Flask, param: str) -> None:
        # Appended twice: redirect_uri/resource are not in _VALID_FORM, so
        # one extra occurrence alone would not make them duplicates.
        duplicate = urllib.parse.urlencode({param: _VALID_FORM.get(param, "anything")})
        body = "&".join((urllib.parse.urlencode(_VALID_FORM), duplicate, duplicate))
        with flask_app.test_request_context(
            method="POST", data=body, content_type=_FORM_CONTENT_TYPE
        ):
            flask_app.preprocess_request()
            OAuthTokenPage(lambda: True).handle_page(PageContext(config=Config(), request=request))

            assert response.status_code == 400
            assert response.json == {"error": "invalid_request"}

    @pytest.mark.parametrize(
        "code_verifier",
        [
            "a" * 42,  # below the 43-character minimum
            "a" * 129,  # above the 128-character maximum
            "a" * 42 + "!",  # character outside the unreserved set
            "a" * 42 + "+",
        ],
    )
    def test_rejects_a_malformed_code_verifier(self, flask_app: Flask, code_verifier: str) -> None:
        with flask_app.test_request_context(
            method="POST", data={**_VALID_FORM, "code_verifier": code_verifier}
        ):
            flask_app.preprocess_request()
            OAuthTokenPage(lambda: True).handle_page(PageContext(config=Config(), request=request))

            assert response.status_code == 400
            assert response.json == {"error": "invalid_request"}

    @pytest.mark.usefixtures("clean_redis")
    @pytest.mark.parametrize("code_verifier", ["a" * 43, "a" * 128])
    def test_accepts_code_verifier_length_boundaries(
        self, flask_app: Flask, code_verifier: str
    ) -> None:
        AuthCodeStore().store(
            _VALID_FORM["code"], _stored_record(code_challenge=_s256_challenge(code_verifier))
        )
        with flask_app.test_request_context(
            method="POST", data={**_VALID_FORM, "code_verifier": code_verifier}
        ):
            flask_app.preprocess_request()
            OAuthTokenPage(lambda: True).handle_page(PageContext(config=Config(), request=request))

            assert response.status_code == 200

    @pytest.mark.usefixtures("clean_redis")
    def test_rejects_a_wrong_code_verifier(self, flask_app: Flask) -> None:
        AuthCodeStore().store(_VALID_FORM["code"], _stored_record())
        with flask_app.test_request_context(
            method="POST", data={**_VALID_FORM, "code_verifier": "b" * 43}
        ):
            flask_app.preprocess_request()
            OAuthTokenPage(lambda: True).handle_page(PageContext(config=Config(), request=request))

            assert response.status_code == 400
            assert response.json == {"error": "invalid_grant"}

    @pytest.mark.usefixtures("clean_redis")
    def test_rejects_a_non_ascii_stored_challenge(self, flask_app: Flask) -> None:
        # The challenge is stored as the client sent it; comparing it must
        # yield invalid_grant, not blow up on the encoding.
        AuthCodeStore().store(_VALID_FORM["code"], _stored_record(code_challenge="ü" * 43))
        with flask_app.test_request_context(method="POST", data=_VALID_FORM):
            flask_app.preprocess_request()
            OAuthTokenPage(lambda: True).handle_page(PageContext(config=Config(), request=request))

            assert response.status_code == 400
            assert response.json == {"error": "invalid_grant"}

    @pytest.mark.usefixtures("clean_redis")
    def test_a_failed_verifier_check_burns_the_code(self, flask_app: Flask) -> None:
        # The code is consumed before verification, so after one wrong
        # attempt even the correct verifier cannot redeem it anymore.
        AuthCodeStore().store(_VALID_FORM["code"], _stored_record())
        with flask_app.test_request_context(
            method="POST", data={**_VALID_FORM, "code_verifier": "b" * 43}
        ):
            flask_app.preprocess_request()
            OAuthTokenPage(lambda: True).handle_page(PageContext(config=Config(), request=request))
            assert response.status_code == 400
            assert response.json == {"error": "invalid_grant"}

        with flask_app.test_request_context(method="POST", data=_VALID_FORM):
            flask_app.preprocess_request()
            OAuthTokenPage(lambda: True).handle_page(PageContext(config=Config(), request=request))

            assert response.status_code == 400
            assert response.json == {"error": "invalid_grant"}

    @pytest.mark.usefixtures("clean_redis")
    def test_rejects_a_client_id_the_code_was_not_issued_to(self, flask_app: Flask) -> None:
        AuthCodeStore().store(_VALID_FORM["code"], _stored_record())
        with flask_app.test_request_context(
            method="POST", data={**_VALID_FORM, "client_id": "other-client"}
        ):
            flask_app.preprocess_request()
            OAuthTokenPage(lambda: True).handle_page(PageContext(config=Config(), request=request))

            assert response.status_code == 400
            assert response.json == {"error": "invalid_grant"}

    @pytest.mark.usefixtures("clean_redis")
    def test_rejects_a_redirect_uri_that_does_not_match_the_stored_one(
        self, flask_app: Flask
    ) -> None:
        AuthCodeStore().store(_VALID_FORM["code"], _stored_record())
        with flask_app.test_request_context(
            method="POST", data={**_VALID_FORM, "redirect_uri": "https://evil.example/callback"}
        ):
            flask_app.preprocess_request()
            OAuthTokenPage(lambda: True).handle_page(PageContext(config=Config(), request=request))

            assert response.status_code == 400
            assert response.json == {"error": "invalid_grant"}

    @pytest.mark.usefixtures("clean_redis")
    def test_accepts_a_redirect_uri_matching_the_stored_one(self, flask_app: Flask) -> None:
        # OAuth 2.0 clients still send redirect_uri (OAuth 2.1 removed it);
        # a matching value must keep working.
        AuthCodeStore().store(_VALID_FORM["code"], _stored_record())
        with flask_app.test_request_context(
            method="POST",
            data={**_VALID_FORM, "redirect_uri": "https://client.example/callback"},
        ):
            flask_app.preprocess_request()
            OAuthTokenPage(lambda: True).handle_page(PageContext(config=Config(), request=request))

            assert response.status_code == 200

    @pytest.mark.usefixtures("clean_redis")
    def test_rejects_a_resource_that_does_not_match_the_stored_one(self, flask_app: Flask) -> None:
        AuthCodeStore().store(_VALID_FORM["code"], _stored_record())
        with flask_app.test_request_context(
            method="POST",
            data={**_VALID_FORM, "resource": "https://host/othersite/check_mk/mcp"},
        ):
            flask_app.preprocess_request()
            OAuthTokenPage(lambda: True).handle_page(PageContext(config=Config(), request=request))

            assert response.status_code == 400
            assert response.json == {"error": "invalid_grant"}

    @pytest.mark.usefixtures("clean_redis")
    def test_accepts_a_resource_matching_the_stored_one(self, flask_app: Flask) -> None:
        AuthCodeStore().store(_VALID_FORM["code"], _stored_record())
        with flask_app.test_request_context(
            method="POST",
            data={**_VALID_FORM, "resource": "https://host/mysite/check_mk/mcp"},
        ):
            flask_app.preprocess_request()
            OAuthTokenPage(lambda: True).handle_page(PageContext(config=Config(), request=request))

            assert response.status_code == 200

    @pytest.mark.usefixtures("clean_redis")
    def test_rejects_a_resource_when_none_was_bound(self, flask_app: Flask) -> None:
        AuthCodeStore().store(_VALID_FORM["code"], _stored_record(resource=None))
        with flask_app.test_request_context(
            method="POST",
            data={**_VALID_FORM, "resource": "https://host/mysite/check_mk/mcp"},
        ):
            flask_app.preprocess_request()
            OAuthTokenPage(lambda: True).handle_page(PageContext(config=Config(), request=request))

            assert response.status_code == 400
            assert response.json == {"error": "invalid_grant"}

    @pytest.mark.usefixtures("clean_redis")
    @pytest.mark.parametrize("param", ["redirect_uri", "resource"])
    def test_treats_an_empty_optional_binding_parameter_as_omitted(
        self, flask_app: Flask, param: str
    ) -> None:
        AuthCodeStore().store(_VALID_FORM["code"], _stored_record())
        with flask_app.test_request_context(method="POST", data={**_VALID_FORM, param: ""}):
            flask_app.preprocess_request()
            OAuthTokenPage(lambda: True).handle_page(PageContext(config=Config(), request=request))

            assert response.status_code == 200

    @pytest.mark.usefixtures("clean_redis")
    def test_ignores_a_scope_parameter(self, flask_app: Flask) -> None:
        # RFC 6749 section 3.2: unrecognized parameters are ignored; scope
        # for the eventual token comes only from the stored record.
        AuthCodeStore().store(_VALID_FORM["code"], _stored_record())
        with flask_app.test_request_context(
            method="POST", data={**_VALID_FORM, "scope": "admin everything"}
        ):
            flask_app.preprocess_request()
            OAuthTokenPage(lambda: True).handle_page(PageContext(config=Config(), request=request))

            assert response.status_code == 200

    @pytest.mark.usefixtures("clean_redis")
    def test_rejects_an_unknown_code(self, flask_app: Flask) -> None:
        with flask_app.test_request_context(method="POST", data=_VALID_FORM):
            flask_app.preprocess_request()
            OAuthTokenPage(lambda: True).handle_page(PageContext(config=Config(), request=request))

            assert response.status_code == 400
            assert response.json == {"error": "invalid_grant"}

    @pytest.mark.usefixtures("clean_redis")
    def test_a_code_can_be_redeemed_only_once(self, flask_app: Flask) -> None:
        AuthCodeStore().store(_VALID_FORM["code"], _stored_record())
        with flask_app.test_request_context(method="POST", data=_VALID_FORM):
            flask_app.preprocess_request()
            OAuthTokenPage(lambda: True).handle_page(PageContext(config=Config(), request=request))
            assert response.status_code == 200

        with flask_app.test_request_context(method="POST", data=_VALID_FORM):
            flask_app.preprocess_request()
            OAuthTokenPage(lambda: True).handle_page(PageContext(config=Config(), request=request))

            assert response.status_code == 400
            assert response.json == {"error": "invalid_grant"}

    @pytest.mark.usefixtures("clean_redis")
    def test_no_token_is_issued_when_the_store_is_unavailable(self, flask_app: Flask) -> None:
        with flask_app.test_request_context(method="POST", data=_VALID_FORM):
            flask_app.preprocess_request()
            with disable_redis():
                OAuthTokenPage(lambda: True).handle_page(
                    PageContext(config=Config(), request=request)
                )

            assert response.status_code == 500
            assert b"access_token" not in response.get_data()

    @pytest.mark.usefixtures("clean_redis")
    def test_logs_security_event_when_the_store_is_unavailable(
        self, flask_app: Flask, mocker: MockerFixture
    ) -> None:
        mock_log = mocker.patch("cmk.gui.oauth.pages._token.log_security_event")
        with flask_app.test_request_context(method="POST", data=_VALID_FORM):
            flask_app.preprocess_request()
            with disable_redis():
                OAuthTokenPage(lambda: True).handle_page(
                    PageContext(config=Config(), request=request)
                )

        mock_log.assert_called_once()
        assert mock_log.call_args.args[0].details["reason"] == "failed to redeem authorization code"

    @pytest.mark.usefixtures("clean_redis")
    def test_treats_a_request_timeout_as_a_store_failure(
        self, flask_app: Flask, mocker: MockerFixture
    ) -> None:
        # A timeout inside consume() takes the store-outage path, not the framework's handling.
        mocker.patch.object(AuthCodeStore, "consume", side_effect=MKTimeout)
        mock_log = mocker.patch("cmk.gui.oauth.pages._token.log_security_event")
        with flask_app.test_request_context(method="POST", data=_VALID_FORM):
            flask_app.preprocess_request()
            OAuthTokenPage(lambda: True).handle_page(PageContext(config=Config(), request=request))

            assert response.status_code == 500

        mock_log.assert_called_once()

    @pytest.mark.usefixtures("clean_redis")
    def test_logs_the_exception_when_the_store_is_unavailable(
        self, flask_app: Flask, mocker: MockerFixture
    ) -> None:
        # The security event carries only a static reason; the log entry with
        # the traceback is the only place the actual cause ends up.
        mock_logger = mocker.patch("cmk.gui.oauth.pages._token.logger")
        with flask_app.test_request_context(method="POST", data=_VALID_FORM):
            flask_app.preprocess_request()
            with disable_redis():
                OAuthTokenPage(lambda: True).handle_page(
                    PageContext(config=Config(), request=request)
                )

        mock_logger.exception.assert_called_once()

    @pytest.mark.usefixtures("clean_redis")
    def test_token_response_is_not_cacheable(self, flask_app: Flask) -> None:
        AuthCodeStore().store(_VALID_FORM["code"], _stored_record())
        with flask_app.test_request_context(method="POST", data=_VALID_FORM):
            flask_app.preprocess_request()
            OAuthTokenPage(lambda: True).handle_page(PageContext(config=Config(), request=request))

            assert response.headers.get("Cache-Control") == "no-store"

    def test_error_response_is_not_cacheable(self, flask_app: Flask) -> None:
        with flask_app.test_request_context(method="POST", data={"grant_type": "refresh_token"}):
            flask_app.preprocess_request()
            OAuthTokenPage(lambda: True).handle_page(PageContext(config=Config(), request=request))

            assert response.headers.get("Cache-Control") == "no-store"
