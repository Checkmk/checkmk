#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re
from collections.abc import Iterator
from html import unescape
from types import SimpleNamespace
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

import pytest
from flask import Flask
from pytest_mock import MockerFixture

from cmk.ccc.exceptions import MKGeneralException, MKTimeout
from cmk.ccc.user import UserId
from cmk.gui import oauth
from cmk.gui.config import Config
from cmk.gui.http import request, response
from cmk.gui.oauth.pages._authorize import OAuthAuthorizePage
from cmk.gui.oauth.store._auth_code_store import AuthCodeRecord, AuthCodeStore
from cmk.gui.pages import PageContext
from cmk.gui.session_context import UserContext
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.utils.transaction_manager import TransactionManager
from cmk.utils.redis import disable_redis, get_redis_client


def _extract_redirect_target(body: str) -> str:
    match = re.search(r'<a[^>]+href="([^"]+)"', body)
    assert match is not None, "no fallback link in the redirect page"
    return unescape(match.group(1))


@pytest.fixture(name="mock_vue_manifest")
def fixture_mock_vue_manifest() -> Iterator[None]:
    # make_header() -> body_start() -> _head() loads the built frontend's
    # Vue manifest unconditionally, even in "static_files" mode. There's no
    # real frontend build in this test sandbox, so stub it out.
    fake_manifest = SimpleNamespace(
        main="cmk-frontend-vue/main.js",
        main_stylesheets=[],
        nav_sidebar="cmk-frontend-vue/nav_sidebar.js",
        nav_sidebar_stylesheets=[],
        stage1="cmk-frontend-vue/stage1.js",
    )
    with patch("cmk.gui.htmllib.html._load_vue_manifest", return_value=fake_manifest):
        yield


_SESSION_USER = UserId("alice")


@pytest.fixture(name="registered_client_id")
def fixture_registered_client_id() -> str:
    return (
        oauth.client_store().register(["https://client.example/callback"], "Test Client").client_id
    )


@pytest.mark.usefixtures("request_context", "mock_vue_manifest")
class TestOAuthAuthorizePage:
    def test_shows_consent_page_on_get(self, flask_app: Flask, registered_client_id: str) -> None:
        with flask_app.test_request_context(
            query_string={
                "redirect_uri": "https://client.example/callback",
                "response_type": "code",
                "client_id": registered_client_id,
                "code_challenge": "test-challenge",
                "code_challenge_method": "S256",
                "state": "xyz",
            }
        ):
            flask_app.preprocess_request()
            OAuthAuthorizePage(lambda: True).handle_page(
                PageContext(config=Config(), request=request)
            )

            assert response.status_code == 200
            body = response.get_data(as_text=True)
            assert "<form" in body
            assert 'name="_authorize"' in body
            assert 'name="_deny"' in body

    @pytest.mark.parametrize(
        "requested_scope, expected_grants",
        [
            # The user is told what they are approving, in the normalized form
            # the code will actually be bound to -- not the client's wording.
            ("read", "read data"),
            ("write", "read data, change data and configuration"),
        ],
    )
    def test_consent_page_lists_the_grants(
        self,
        flask_app: Flask,
        registered_client_id: str,
        requested_scope: str,
        expected_grants: str,
    ) -> None:
        with flask_app.test_request_context(
            query_string={
                "redirect_uri": "https://client.example/callback",
                "response_type": "code",
                "client_id": registered_client_id,
                "code_challenge": "test-challenge",
                "code_challenge_method": "S256",
                "scope": requested_scope,
            }
        ):
            flask_app.preprocess_request()
            OAuthAuthorizePage(lambda: True).handle_page(
                PageContext(config=Config(), request=request)
            )

            assert response.status_code == 200
            body = response.get_data(as_text=True)
            assert f"It is requesting permission to: {expected_grants}." in body

    def test_redirects_with_invalid_scope_when_the_scope_is_unknown(
        self, flask_app: Flask, registered_client_id: str
    ) -> None:
        # Both metadata documents advertise what this server accepts, so an
        # unknown scope is a client bug. Rejecting it here beats downscoping
        # and letting the client discover the gap on its first write.
        with flask_app.test_request_context(
            query_string={
                "redirect_uri": "https://client.example/callback",
                "response_type": "code",
                "client_id": registered_client_id,
                "code_challenge": "test-challenge",
                "code_challenge_method": "S256",
                "scope": "mcp",
            }
        ):
            flask_app.preprocess_request()
            OAuthAuthorizePage(lambda: True).handle_page(
                PageContext(config=Config(), request=request)
            )

            target_url = _extract_redirect_target(response.get_data(as_text=True))

        assert parse_qs(urlsplit(target_url).query)["error"] == ["invalid_scope"]

    def test_redirects_with_invalid_request_when_scope_is_repeated(
        self, flask_app: Flask, registered_client_id: str
    ) -> None:
        # With two scope values there is no single answer to what the user is
        # approving, so the request is rejected rather than resolved to one.
        with flask_app.test_request_context(
            query_string=(
                "redirect_uri=https://client.example/callback"
                "&response_type=code"
                f"&client_id={registered_client_id}"
                "&code_challenge=test-challenge"
                "&code_challenge_method=S256"
                "&scope=read&scope=write"
            )
        ):
            flask_app.preprocess_request()
            OAuthAuthorizePage(lambda: True).handle_page(
                PageContext(config=Config(), request=request)
            )

            target_url = _extract_redirect_target(response.get_data(as_text=True))

        assert parse_qs(urlsplit(target_url).query)["error"] == ["invalid_request"]

    def test_consent_form_posts_back_to_the_request_path(
        self, flask_app: Flask, registered_client_id: str
    ) -> None:
        # Reached via the external OAuth issuer alias (/oauth-<site>/authorize,
        # see system_apache.py), not the backend's own /check_mk/oauth_authorize.py
        # path. The form must submit back to this same alias, not a relative
        # "oauth_authorize.py" that would resolve against the wrong base path.
        with flask_app.test_request_context(
            path="/oauth-heute/authorize",
            query_string={
                "redirect_uri": "https://client.example/callback",
                "response_type": "code",
                "client_id": registered_client_id,
                "code_challenge": "test-challenge",
                "code_challenge_method": "S256",
            },
        ):
            flask_app.preprocess_request()
            OAuthAuthorizePage(lambda: True).handle_page(
                PageContext(config=Config(), request=request)
            )

            assert 'action="/oauth-heute/authorize"' in response.get_data(as_text=True)

    @pytest.mark.usefixtures("clean_redis")
    def test_redirects_with_code_once_confirmed(
        self, flask_app: Flask, registered_client_id: str
    ) -> None:
        with (
            patch.object(TransactionManager, "check_transaction", return_value=True),
            patch("cmk.gui.oauth.pages._authorize.check_csrf_token"),
            flask_app.test_request_context(
                method="POST",
                data={
                    "redirect_uri": "https://client.example/callback",
                    "response_type": "code",
                    "client_id": registered_client_id,
                    "code_challenge": "test-challenge",
                    "code_challenge_method": "S256",
                    "state": "xyz",
                },
            ),
        ):
            flask_app.preprocess_request()
            with UserContext(_SESSION_USER, UserPermissions({}, {}, {}, [])):
                OAuthAuthorizePage(lambda: True).handle_page(
                    PageContext(config=Config(), request=request)
                )

            assert response.status_code == 200
            target_url = _extract_redirect_target(response.get_data(as_text=True))

        parts = urlsplit(target_url)
        assert f"{parts.scheme}://{parts.netloc}{parts.path}" == "https://client.example/callback"
        query = parse_qs(parts.query)
        assert query["state"] == ["xyz"]
        assert query["code"][0]

    @pytest.mark.usefixtures("clean_redis")
    def test_rejects_post_without_a_valid_csrf_token(
        self, flask_app: Flask, registered_client_id: str
    ) -> None:
        with (
            patch.object(TransactionManager, "check_transaction", return_value=True),
            flask_app.test_request_context(
                method="POST",
                data={
                    "redirect_uri": "https://client.example/callback",
                    "response_type": "code",
                    "client_id": registered_client_id,
                    "code_challenge": "test-challenge",
                    "code_challenge_method": "S256",
                },
            ),
        ):
            flask_app.preprocess_request()
            with (
                UserContext(_SESSION_USER, UserPermissions({}, {}, {}, [])),
                pytest.raises(MKGeneralException, match="CSRF"),
            ):
                OAuthAuthorizePage(lambda: True).handle_page(
                    PageContext(config=Config(), request=request)
                )

        assert get_redis_client().keys() == []

    def test_redirects_with_access_denied_when_denied(
        self, flask_app: Flask, registered_client_id: str
    ) -> None:
        with (
            patch.object(TransactionManager, "check_transaction", return_value=True),
            flask_app.test_request_context(
                method="POST",
                data={
                    "redirect_uri": "https://client.example/callback",
                    "response_type": "code",
                    "client_id": registered_client_id,
                    "code_challenge": "test-challenge",
                    "code_challenge_method": "S256",
                    "state": "xyz",
                    "_deny": "Deny",
                },
            ),
        ):
            flask_app.preprocess_request()
            OAuthAuthorizePage(lambda: True).handle_page(
                PageContext(config=Config(), request=request)
            )

            assert response.status_code == 200
            target_url = _extract_redirect_target(response.get_data(as_text=True))

        parts = urlsplit(target_url)
        assert f"{parts.scheme}://{parts.netloc}{parts.path}" == "https://client.example/callback"
        query = parse_qs(parts.query)
        assert query["error"] == ["access_denied"]
        assert query["state"] == ["xyz"]
        assert "code" not in query

    @pytest.mark.usefixtures("clean_redis")
    def test_preserves_existing_query_params_on_redirect_uri(self, flask_app: Flask) -> None:
        client_id = (
            oauth.client_store()
            .register(["https://client.example/callback?foo=bar"], None)
            .client_id
        )
        with (
            patch.object(TransactionManager, "check_transaction", return_value=True),
            patch("cmk.gui.oauth.pages._authorize.check_csrf_token"),
            flask_app.test_request_context(
                method="POST",
                data={
                    "redirect_uri": "https://client.example/callback?foo=bar",
                    "response_type": "code",
                    "client_id": client_id,
                    "code_challenge": "test-challenge",
                    "code_challenge_method": "S256",
                },
            ),
        ):
            flask_app.preprocess_request()
            with UserContext(_SESSION_USER, UserPermissions({}, {}, {}, [])):
                OAuthAuthorizePage(lambda: True).handle_page(
                    PageContext(config=Config(), request=request)
                )

            target_url = _extract_redirect_target(response.get_data(as_text=True))

        query = parse_qs(urlsplit(target_url).query)
        assert query["foo"] == ["bar"]
        assert query["code"][0]

    @pytest.mark.usefixtures("clean_redis")
    def test_redirect_page_is_not_an_http_redirect(
        self, flask_app: Flask, registered_client_id: str
    ) -> None:
        # Regression test: an HTTP 3xx here would carry the site's
        # form-action CSP over onto this cross-origin hop, and Chrome (unlike
        # Firefox) enforces that directive against redirects resulting from
        # a form submission -- blocking the navigation to redirect_uri since
        # it's necessarily a different origin (the OAuth client's callback).
        with (
            patch.object(TransactionManager, "check_transaction", return_value=True),
            patch("cmk.gui.oauth.pages._authorize.check_csrf_token"),
            flask_app.test_request_context(
                method="POST",
                data={
                    "redirect_uri": "https://client.example/callback",
                    "response_type": "code",
                    "client_id": registered_client_id,
                    "code_challenge": "test-challenge",
                    "code_challenge_method": "S256",
                },
            ),
        ):
            flask_app.preprocess_request()
            with UserContext(_SESSION_USER, UserPermissions({}, {}, {}, [])):
                OAuthAuthorizePage(lambda: True).handle_page(
                    PageContext(config=Config(), request=request)
                )

            assert response.status_code == 200
            body = response.get_data(as_text=True)
            assert 'http-equiv="refresh"' in body

    def test_shows_consent_page_again_when_not_confirmed(
        self, flask_app: Flask, registered_client_id: str
    ) -> None:
        with (
            patch.object(TransactionManager, "check_transaction", return_value=False),
            flask_app.test_request_context(
                method="POST",
                data={
                    "redirect_uri": "https://client.example/callback",
                    "response_type": "code",
                    "client_id": registered_client_id,
                    "code_challenge": "test-challenge",
                    "code_challenge_method": "S256",
                },
            ),
        ):
            flask_app.preprocess_request()
            OAuthAuthorizePage(lambda: True).handle_page(
                PageContext(config=Config(), request=request)
            )

            assert response.status_code == 200
            assert "<form" in response.get_data(as_text=True)

    def test_redirects_with_invalid_request_when_response_type_is_missing(
        self, flask_app: Flask, registered_client_id: str
    ) -> None:
        with flask_app.test_request_context(
            query_string={
                "redirect_uri": "https://client.example/callback",
                "client_id": registered_client_id,
                "state": "xyz",
            }
        ):
            flask_app.preprocess_request()
            OAuthAuthorizePage(lambda: True).handle_page(
                PageContext(config=Config(), request=request)
            )

            assert response.status_code == 200
            target_url = _extract_redirect_target(response.get_data(as_text=True))

        query = parse_qs(urlsplit(target_url).query)
        assert query["error"] == ["invalid_request"]
        assert query["state"] == ["xyz"]

    def test_redirects_with_unsupported_response_type_when_not_code(
        self, flask_app: Flask, registered_client_id: str
    ) -> None:
        with flask_app.test_request_context(
            query_string={
                "redirect_uri": "https://client.example/callback",
                "response_type": "token",
                "client_id": registered_client_id,
                "state": "xyz",
            }
        ):
            flask_app.preprocess_request()
            OAuthAuthorizePage(lambda: True).handle_page(
                PageContext(config=Config(), request=request)
            )

            assert response.status_code == 200
            target_url = _extract_redirect_target(response.get_data(as_text=True))

        query = parse_qs(urlsplit(target_url).query)
        assert query["error"] == ["unsupported_response_type"]
        assert query["state"] == ["xyz"]

    def test_returns_400_when_client_id_is_missing(self, flask_app: Flask) -> None:
        # RFC 6749 section 4.1.2.1: missing client_id must not redirect either.
        with flask_app.test_request_context(
            query_string={
                "redirect_uri": "https://client.example/callback",
                "response_type": "code",
                "state": "xyz",
            }
        ):
            flask_app.preprocess_request()
            OAuthAuthorizePage(lambda: True).handle_page(
                PageContext(config=Config(), request=request)
            )

            assert response.status_code == 400

    def test_returns_400_when_client_id_is_unknown(self, flask_app: Flask) -> None:
        with flask_app.test_request_context(
            query_string={
                "redirect_uri": "https://client.example/callback",
                "response_type": "code",
                "client_id": "never-registered-client",
                "state": "xyz",
            }
        ):
            flask_app.preprocess_request()
            OAuthAuthorizePage(lambda: True).handle_page(
                PageContext(config=Config(), request=request)
            )

            assert response.status_code == 400

    def test_returns_400_when_redirect_uri_does_not_match_registered_client(
        self, flask_app: Flask, registered_client_id: str
    ) -> None:
        with flask_app.test_request_context(
            query_string={
                "redirect_uri": "https://attacker.example/callback",
                "response_type": "code",
                "client_id": registered_client_id,
                "state": "xyz",
            }
        ):
            flask_app.preprocess_request()
            OAuthAuthorizePage(lambda: True).handle_page(
                PageContext(config=Config(), request=request)
            )

            assert response.status_code == 400

    def test_redirects_with_invalid_request_when_code_challenge_is_missing(
        self, flask_app: Flask, registered_client_id: str
    ) -> None:
        with flask_app.test_request_context(
            query_string={
                "redirect_uri": "https://client.example/callback",
                "response_type": "code",
                "client_id": registered_client_id,
                "state": "xyz",
            }
        ):
            flask_app.preprocess_request()
            OAuthAuthorizePage(lambda: True).handle_page(
                PageContext(config=Config(), request=request)
            )

            assert response.status_code == 200
            target_url = _extract_redirect_target(response.get_data(as_text=True))

        query = parse_qs(urlsplit(target_url).query)
        assert query["error"] == ["invalid_request"]
        assert query["state"] == ["xyz"]

    def test_redirects_with_invalid_request_when_code_challenge_method_is_missing(
        self, flask_app: Flask, registered_client_id: str
    ) -> None:
        with flask_app.test_request_context(
            query_string={
                "redirect_uri": "https://client.example/callback",
                "response_type": "code",
                "client_id": registered_client_id,
                "code_challenge": "test-challenge",
                "state": "xyz",
            }
        ):
            flask_app.preprocess_request()
            OAuthAuthorizePage(lambda: True).handle_page(
                PageContext(config=Config(), request=request)
            )

            assert response.status_code == 200
            target_url = _extract_redirect_target(response.get_data(as_text=True))

        query = parse_qs(urlsplit(target_url).query)
        assert query["error"] == ["invalid_request"]
        assert query["state"] == ["xyz"]

    def test_redirects_with_invalid_request_when_code_challenge_method_is_plain(
        self, flask_app: Flask, registered_client_id: str
    ) -> None:
        with flask_app.test_request_context(
            query_string={
                "redirect_uri": "https://client.example/callback",
                "response_type": "code",
                "client_id": registered_client_id,
                "code_challenge": "test-challenge",
                "code_challenge_method": "plain",
                "state": "xyz",
            }
        ):
            flask_app.preprocess_request()
            OAuthAuthorizePage(lambda: True).handle_page(
                PageContext(config=Config(), request=request)
            )

            assert response.status_code == 200
            target_url = _extract_redirect_target(response.get_data(as_text=True))

        query = parse_qs(urlsplit(target_url).query)
        assert query["error"] == ["invalid_request"]
        assert query["state"] == ["xyz"]

    def test_returns_400_when_redirect_uri_missing(self, flask_app: Flask) -> None:
        with flask_app.test_request_context():
            flask_app.preprocess_request()
            OAuthAuthorizePage(lambda: True).handle_page(
                PageContext(config=Config(), request=request)
            )

            assert response.status_code == 400

    def test_returns_400_when_redirect_uri_scheme_is_not_http_or_https(
        self, flask_app: Flask
    ) -> None:
        # Regression test: redirect_uri ends up in a href/content attribute
        # on the redirect page. HTML-escaping alone doesn't stop a
        # javascript: URI from executing if that link is followed.
        with flask_app.test_request_context(
            query_string={"redirect_uri": "javascript:alert(document.cookie)"}
        ):
            flask_app.preprocess_request()
            OAuthAuthorizePage(lambda: True).handle_page(
                PageContext(config=Config(), request=request)
            )

            assert response.status_code == 400

    def test_returns_404_when_disabled(self, flask_app: Flask) -> None:
        with flask_app.test_request_context(
            query_string={"redirect_uri": "https://client.example/callback"}
        ):
            flask_app.preprocess_request()
            OAuthAuthorizePage(lambda: False).handle_page(
                PageContext(config=Config(), request=request)
            )

            assert response.status_code == 404

    def test_logs_security_event_when_redirect_uri_is_invalid(
        self, flask_app: Flask, mocker: MockerFixture
    ) -> None:
        mock_log = mocker.patch("cmk.gui.oauth.pages._authorize.log_security_event")
        with flask_app.test_request_context(query_string={"redirect_uri": "javascript:alert(1)"}):
            flask_app.preprocess_request()
            OAuthAuthorizePage(lambda: True).handle_page(
                PageContext(config=Config(), request=request)
            )

        mock_log.assert_called_once()
        assert mock_log.call_args.args[0].details["reason"] == "invalid or missing redirect_uri"

    def test_logs_which_scope_was_rejected(
        self, flask_app: Flask, mocker: MockerFixture, registered_client_id: str
    ) -> None:
        # A report that a client asked for a scope we don't have is only
        # actionable if it says which one.
        mock_log = mocker.patch("cmk.gui.oauth.pages._authorize.log_security_event")
        with flask_app.test_request_context(
            query_string={
                "redirect_uri": "https://client.example/callback",
                "response_type": "code",
                "client_id": registered_client_id,
                "code_challenge": "test-challenge",
                "code_challenge_method": "S256",
                "scope": "read mcp",
            }
        ):
            flask_app.preprocess_request()
            OAuthAuthorizePage(lambda: True).handle_page(
                PageContext(config=Config(), request=request)
            )

        mock_log.assert_called_once()
        assert mock_log.call_args.args[0].details["reason"] == "unknown scope: mcp"

    def test_logs_security_event_when_response_type_is_missing(
        self, flask_app: Flask, mocker: MockerFixture, registered_client_id: str
    ) -> None:
        mock_log = mocker.patch("cmk.gui.oauth.pages._authorize.log_security_event")
        with flask_app.test_request_context(
            query_string={
                "redirect_uri": "https://client.example/callback",
                "client_id": registered_client_id,
            }
        ):
            flask_app.preprocess_request()
            OAuthAuthorizePage(lambda: True).handle_page(
                PageContext(config=Config(), request=request)
            )

        mock_log.assert_called_once()
        assert mock_log.call_args.args[0].details["reason"] == "missing response_type"

    def test_logs_security_event_when_response_type_is_unsupported(
        self, flask_app: Flask, mocker: MockerFixture, registered_client_id: str
    ) -> None:
        mock_log = mocker.patch("cmk.gui.oauth.pages._authorize.log_security_event")
        with flask_app.test_request_context(
            query_string={
                "redirect_uri": "https://client.example/callback",
                "client_id": registered_client_id,
                "response_type": "token",
            }
        ):
            flask_app.preprocess_request()
            OAuthAuthorizePage(lambda: True).handle_page(
                PageContext(config=Config(), request=request)
            )

        mock_log.assert_called_once()
        assert mock_log.call_args.args[0].details["reason"] == "unsupported response_type"

    def test_logs_security_event_when_client_id_is_missing(
        self, flask_app: Flask, mocker: MockerFixture
    ) -> None:
        mock_log = mocker.patch("cmk.gui.oauth.pages._authorize.log_security_event")
        with flask_app.test_request_context(
            query_string={"redirect_uri": "https://client.example/callback"}
        ):
            flask_app.preprocess_request()
            OAuthAuthorizePage(lambda: True).handle_page(
                PageContext(config=Config(), request=request)
            )

        mock_log.assert_called_once()
        assert mock_log.call_args.args[0].details["reason"] == "missing client_id"

    def test_logs_security_event_when_client_id_is_unknown(
        self, flask_app: Flask, mocker: MockerFixture
    ) -> None:
        mock_log = mocker.patch("cmk.gui.oauth.pages._authorize.log_security_event")
        with flask_app.test_request_context(
            query_string={
                "redirect_uri": "https://client.example/callback",
                "client_id": "never-registered-client",
            }
        ):
            flask_app.preprocess_request()
            OAuthAuthorizePage(lambda: True).handle_page(
                PageContext(config=Config(), request=request)
            )

        mock_log.assert_called_once()
        assert mock_log.call_args.args[0].details["reason"] == "unknown client_id"

    def test_logs_security_event_when_redirect_uri_does_not_match_registered_client(
        self, flask_app: Flask, mocker: MockerFixture, registered_client_id: str
    ) -> None:
        mock_log = mocker.patch("cmk.gui.oauth.pages._authorize.log_security_event")
        with flask_app.test_request_context(
            query_string={
                "redirect_uri": "https://attacker.example/callback",
                "client_id": registered_client_id,
            }
        ):
            flask_app.preprocess_request()
            OAuthAuthorizePage(lambda: True).handle_page(
                PageContext(config=Config(), request=request)
            )

        mock_log.assert_called_once()
        assert (
            mock_log.call_args.args[0].details["reason"]
            == "redirect_uri not registered for client_id"
        )

    def test_logs_security_event_when_code_challenge_is_missing(
        self, flask_app: Flask, mocker: MockerFixture, registered_client_id: str
    ) -> None:
        mock_log = mocker.patch("cmk.gui.oauth.pages._authorize.log_security_event")
        with flask_app.test_request_context(
            query_string={
                "redirect_uri": "https://client.example/callback",
                "client_id": registered_client_id,
                "response_type": "code",
            }
        ):
            flask_app.preprocess_request()
            OAuthAuthorizePage(lambda: True).handle_page(
                PageContext(config=Config(), request=request)
            )

        mock_log.assert_called_once()
        assert mock_log.call_args.args[0].details["reason"] == "missing code_challenge"

    @pytest.mark.usefixtures("clean_redis")
    def test_approve_persists_the_issued_code_bound_to_the_request(
        self, flask_app: Flask, registered_client_id: str
    ) -> None:
        with (
            patch.object(TransactionManager, "check_transaction", return_value=True),
            patch("cmk.gui.oauth.pages._authorize.check_csrf_token"),
            flask_app.test_request_context(
                method="POST",
                data={
                    "redirect_uri": "https://client.example/callback",
                    "response_type": "code",
                    "client_id": registered_client_id,
                    "code_challenge": "test-challenge",
                    "code_challenge_method": "S256",
                    "scope": "read",
                    "resource": "https://host/mysite/check_mk/mcp",
                },
            ),
        ):
            flask_app.preprocess_request()
            with UserContext(_SESSION_USER, UserPermissions({}, {}, {}, [])):
                OAuthAuthorizePage(lambda: True).handle_page(
                    PageContext(config=Config(), request=request)
                )

            target_url = _extract_redirect_target(response.get_data(as_text=True))

        code = parse_qs(urlsplit(target_url).query)["code"][0]
        assert AuthCodeStore().consume(code) == AuthCodeRecord(
            user_id=_SESSION_USER,
            client_id=registered_client_id,
            redirect_uri="https://client.example/callback",
            scope="read",
            resource="https://host/mysite/check_mk/mcp",
            code_challenge="test-challenge",
        )

    @pytest.mark.usefixtures("clean_redis")
    def test_approve_binds_the_normalized_scope(
        self, flask_app: Flask, registered_client_id: str
    ) -> None:
        # A client asking to write is granted read as well -- one grant, one
        # spelling, decided here rather than at redemption.
        with (
            patch.object(TransactionManager, "check_transaction", return_value=True),
            patch("cmk.gui.oauth.pages._authorize.check_csrf_token"),
            flask_app.test_request_context(
                method="POST",
                data={
                    "redirect_uri": "https://client.example/callback",
                    "response_type": "code",
                    "client_id": registered_client_id,
                    "code_challenge": "test-challenge",
                    "code_challenge_method": "S256",
                    "scope": "write",
                },
            ),
        ):
            flask_app.preprocess_request()
            with UserContext(_SESSION_USER, UserPermissions({}, {}, {}, [])):
                OAuthAuthorizePage(lambda: True).handle_page(
                    PageContext(config=Config(), request=request)
                )

            target_url = _extract_redirect_target(response.get_data(as_text=True))

        code = parse_qs(urlsplit(target_url).query)["code"][0]
        record = AuthCodeStore().consume(code)
        assert record is not None
        assert record.scope == "read write"

    @pytest.mark.usefixtures("clean_redis")
    @pytest.mark.parametrize(
        "scope_param",
        [
            pytest.param({}, id="absent"),
            pytest.param({"scope": "   "}, id="blank"),
        ],
    )
    def test_approve_without_scope_binds_the_default_scope(
        self, flask_app: Flask, registered_client_id: str, scope_param: dict[str, str]
    ) -> None:
        with (
            patch.object(TransactionManager, "check_transaction", return_value=True),
            patch("cmk.gui.oauth.pages._authorize.check_csrf_token"),
            flask_app.test_request_context(
                method="POST",
                data={
                    "redirect_uri": "https://client.example/callback",
                    "response_type": "code",
                    "client_id": registered_client_id,
                    "code_challenge": "test-challenge",
                    "code_challenge_method": "S256",
                    **scope_param,
                },
            ),
        ):
            flask_app.preprocess_request()
            with UserContext(_SESSION_USER, UserPermissions({}, {}, {}, [])):
                OAuthAuthorizePage(lambda: True).handle_page(
                    PageContext(config=Config(), request=request)
                )

            target_url = _extract_redirect_target(response.get_data(as_text=True))

        code = parse_qs(urlsplit(target_url).query)["code"][0]
        record = AuthCodeStore().consume(code)
        assert record is not None
        # An absent scope is a read grant (RFC 6749 section 3.3 allows a
        # server-defined default), so unlike resource it never binds None.
        assert record.scope == "read"
        assert record.resource is None

    @pytest.mark.usefixtures("clean_redis")
    def test_deny_persists_nothing(self, flask_app: Flask, registered_client_id: str) -> None:
        with (
            patch.object(TransactionManager, "check_transaction", return_value=True),
            patch("cmk.gui.oauth.pages._authorize.check_csrf_token"),
            flask_app.test_request_context(
                method="POST",
                data={
                    "redirect_uri": "https://client.example/callback",
                    "response_type": "code",
                    "client_id": registered_client_id,
                    "code_challenge": "test-challenge",
                    "code_challenge_method": "S256",
                    "_deny": "Deny",
                },
            ),
        ):
            flask_app.preprocess_request()
            with UserContext(_SESSION_USER, UserPermissions({}, {}, {}, [])):
                OAuthAuthorizePage(lambda: True).handle_page(
                    PageContext(config=Config(), request=request)
                )

        assert get_redis_client().keys() == []

    @pytest.mark.usefixtures("clean_redis")
    def test_no_code_is_issued_when_the_store_is_unavailable(
        self, flask_app: Flask, registered_client_id: str
    ) -> None:
        with (
            patch.object(TransactionManager, "check_transaction", return_value=True),
            patch("cmk.gui.oauth.pages._authorize.check_csrf_token"),
            flask_app.test_request_context(
                method="POST",
                data={
                    "redirect_uri": "https://client.example/callback",
                    "response_type": "code",
                    "client_id": registered_client_id,
                    "code_challenge": "test-challenge",
                    "code_challenge_method": "S256",
                    "state": "xyz",
                },
            ),
        ):
            flask_app.preprocess_request()
            with (
                UserContext(_SESSION_USER, UserPermissions({}, {}, {}, [])),
                disable_redis(),
            ):
                OAuthAuthorizePage(lambda: True).handle_page(
                    PageContext(config=Config(), request=request)
                )

            target_url = _extract_redirect_target(response.get_data(as_text=True))

        query = parse_qs(urlsplit(target_url).query)
        assert query["error"] == ["server_error"]
        assert query["state"] == ["xyz"]
        assert "code" not in query

    @pytest.mark.usefixtures("clean_redis")
    def test_logs_security_event_when_the_store_is_unavailable(
        self, flask_app: Flask, mocker: MockerFixture, registered_client_id: str
    ) -> None:
        mock_log = mocker.patch("cmk.gui.oauth.pages._authorize.log_security_event")
        with (
            patch.object(TransactionManager, "check_transaction", return_value=True),
            patch("cmk.gui.oauth.pages._authorize.check_csrf_token"),
            flask_app.test_request_context(
                method="POST",
                data={
                    "redirect_uri": "https://client.example/callback",
                    "response_type": "code",
                    "client_id": registered_client_id,
                    "code_challenge": "test-challenge",
                    "code_challenge_method": "S256",
                },
            ),
        ):
            flask_app.preprocess_request()
            with (
                UserContext(_SESSION_USER, UserPermissions({}, {}, {}, [])),
                disable_redis(),
            ):
                OAuthAuthorizePage(lambda: True).handle_page(
                    PageContext(config=Config(), request=request)
                )

        mock_log.assert_called_once()
        assert (
            mock_log.call_args.args[0].details["reason"] == "failed to persist authorization code"
        )

    @pytest.mark.usefixtures("clean_redis")
    def test_logs_the_exception_when_the_store_is_unavailable(
        self, flask_app: Flask, mocker: MockerFixture, registered_client_id: str
    ) -> None:
        # The security event carries only a static reason; the log entry with
        # the traceback is the only place the actual cause ends up.
        mock_logger = mocker.patch("cmk.gui.oauth.pages._authorize.logger")
        with (
            patch.object(TransactionManager, "check_transaction", return_value=True),
            patch("cmk.gui.oauth.pages._authorize.check_csrf_token"),
            flask_app.test_request_context(
                method="POST",
                data={
                    "redirect_uri": "https://client.example/callback",
                    "response_type": "code",
                    "client_id": registered_client_id,
                    "code_challenge": "test-challenge",
                    "code_challenge_method": "S256",
                },
            ),
        ):
            flask_app.preprocess_request()
            with (
                UserContext(_SESSION_USER, UserPermissions({}, {}, {}, [])),
                disable_redis(),
            ):
                OAuthAuthorizePage(lambda: True).handle_page(
                    PageContext(config=Config(), request=request)
                )

        mock_logger.exception.assert_called_once()

    @pytest.mark.usefixtures("clean_redis")
    def test_treats_a_request_timeout_as_a_store_failure(
        self, flask_app: Flask, mocker: MockerFixture, registered_client_id: str
    ) -> None:
        # A timeout inside store() takes the store-outage path, not the framework's handling.
        mocker.patch.object(AuthCodeStore, "store", side_effect=MKTimeout)
        with (
            patch.object(TransactionManager, "check_transaction", return_value=True),
            patch("cmk.gui.oauth.pages._authorize.check_csrf_token"),
            flask_app.test_request_context(
                method="POST",
                data={
                    "redirect_uri": "https://client.example/callback",
                    "response_type": "code",
                    "client_id": registered_client_id,
                    "code_challenge": "test-challenge",
                    "code_challenge_method": "S256",
                },
            ),
        ):
            flask_app.preprocess_request()
            with UserContext(_SESSION_USER, UserPermissions({}, {}, {}, [])):
                OAuthAuthorizePage(lambda: True).handle_page(
                    PageContext(config=Config(), request=request)
                )

            target_url = _extract_redirect_target(response.get_data(as_text=True))

        assert parse_qs(urlsplit(target_url).query)["error"] == ["server_error"]

    def test_logs_security_event_when_code_challenge_method_is_unsupported(
        self, flask_app: Flask, mocker: MockerFixture, registered_client_id: str
    ) -> None:
        mock_log = mocker.patch("cmk.gui.oauth.pages._authorize.log_security_event")
        with flask_app.test_request_context(
            query_string={
                "redirect_uri": "https://client.example/callback",
                "client_id": registered_client_id,
                "response_type": "code",
                "code_challenge": "test-challenge",
                "code_challenge_method": "plain",
            }
        ):
            flask_app.preprocess_request()
            OAuthAuthorizePage(lambda: True).handle_page(
                PageContext(config=Config(), request=request)
            )

        mock_log.assert_called_once()
        assert mock_log.call_args.args[0].details["reason"] == "unsupported code_challenge_method"
