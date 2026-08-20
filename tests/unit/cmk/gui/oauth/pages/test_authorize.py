#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import re
from collections.abc import Iterator
from html import unescape
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from urllib.parse import parse_qs, urlsplit

import pytest
from flask import Flask
from pytest_mock import MockerFixture

from cmk.ccc.exceptions import MKGeneralException, MKTimeout
from cmk.ccc.user import UserId
from cmk.gui.config import Config
from cmk.gui.http import request, response
from cmk.gui.oauth.pages._authorize import OAuthAuthorizePage
from cmk.gui.oauth.store._auth_code_store import AuthCodeRecord, AuthCodeStore
from cmk.gui.oauth.store.client_store import get_client_store
from cmk.gui.pages import PageContext
from cmk.gui.session_context import UserContext
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.utils.transaction_manager import TransactionManager
from cmk.utils.redis import disable_redis, get_redis_client

_SESSION_USER = UserId("alice")
_REDIRECT_URI = "https://client.example/callback"


def _authorize_request(
    *,
    client_id: str | None,
    redirect_uri: str | None = _REDIRECT_URI,
    response_type: str | None = "code",
    code_challenge: str | None = "test-challenge",
    code_challenge_method: str | None = "S256",
    scope: str | None = None,
    state: str | None = None,
    resource: str | None = None,
    deny: str | None = None,
) -> dict[str, str]:
    params: dict[str, str | None] = {
        "redirect_uri": redirect_uri,
        "response_type": response_type,
        "client_id": client_id,
        "code_challenge": code_challenge,
        "code_challenge_method": code_challenge_method,
        "scope": scope,
        "state": state,
        "resource": resource,
        "_deny": deny,
    }
    return {name: value for name, value in params.items() if value is not None}


def _extract_redirect_target(body: str) -> str:
    match = re.search(r'<a[^>]+href="([^"]+)"', body)
    assert match is not None, "no fallback link in the redirect page"
    return unescape(match.group(1))


def _logged_reason(security_log: MagicMock) -> str:
    security_log.assert_called_once()
    reason = security_log.call_args.args[0].details["reason"]
    assert isinstance(reason, str)
    return reason


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


@pytest.fixture(name="registered_client_id")
def fixture_registered_client_id() -> str:
    with get_client_store() as store:
        registration = store.register([_REDIRECT_URI], "Test Client")
        assert registration.is_ok()
        return registration.ok.client_id


@pytest.fixture(name="valid_transaction")
def fixture_valid_transaction() -> Iterator[None]:
    # The transaction id lives in the form the page renders, and the tests here
    # build their POST by hand, so the check it exists for is stubbed out.
    with patch.object(TransactionManager, "check_transaction", return_value=True):
        yield


@pytest.fixture(name="valid_csrf_token")
def fixture_valid_csrf_token() -> Iterator[None]:
    # Stubbed for the same reason as valid_transaction. The real check is
    # covered by test_rejects_post_without_a_valid_csrf_token, which is the one
    # POST test that does not ask for this fixture.
    with patch("cmk.gui.oauth.pages._authorize.check_csrf_token"):
        yield


@pytest.fixture(name="security_log")
def fixture_security_log(mocker: MockerFixture) -> MagicMock:
    return mocker.patch("cmk.gui.oauth.pages._authorize.log_security_event")


@pytest.mark.usefixtures("mock_vue_manifest")
class TestOAuthAuthorizePage:
    def test_shows_consent_page_on_get(self, flask_app: Flask, registered_client_id: str) -> None:
        with flask_app.test_request_context(
            query_string=_authorize_request(client_id=registered_client_id, state="xyz")
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

    def test_answers_head_like_get(self, flask_app: Flask, registered_client_id: str) -> None:
        # Werkzeug adds HEAD to every GET route, so turning it away would fail a
        # request clients are free to make.
        with flask_app.test_request_context(
            method="HEAD", query_string=_authorize_request(client_id=registered_client_id)
        ):
            flask_app.preprocess_request()
            OAuthAuthorizePage(lambda: True).handle_page(
                PageContext(config=Config(), request=request)
            )

            assert response.status_code == 200

    @pytest.mark.parametrize("method", ["PUT", "DELETE"])
    def test_rejects_the_verbs_the_endpoint_does_not_define(
        self, flask_app: Flask, registered_client_id: str, method: str
    ) -> None:
        # RFC 6749 section 3.1 gives this endpoint GET and POST, and the site
        # routes the rest here all the same.
        with flask_app.test_request_context(
            method=method, query_string=_authorize_request(client_id=registered_client_id)
        ):
            flask_app.preprocess_request()
            OAuthAuthorizePage(lambda: True).handle_page(
                PageContext(config=Config(), request=request)
            )

            assert response.status_code == 405

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
            query_string=_authorize_request(client_id=registered_client_id, scope=requested_scope)
        ):
            flask_app.preprocess_request()
            OAuthAuthorizePage(lambda: True).handle_page(
                PageContext(config=Config(), request=request)
            )

            assert response.status_code == 200
            body = response.get_data(as_text=True)
            assert f"It is requesting permission to: {expected_grants}." in body

    def test_redirects_with_invalid_request_when_scope_is_repeated(
        self, flask_app: Flask, registered_client_id: str
    ) -> None:
        # A repeated *parameter*, which RFC 6749 section 3.1 forbids outright:
        # with two of them there is no single answer to what the user is
        # approving. Hand-built rather than a case of the table below, because
        # a parameter dict cannot carry the same name twice.
        with flask_app.test_request_context(
            query_string=(
                f"redirect_uri={_REDIRECT_URI}"
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
            query_string=_authorize_request(client_id=registered_client_id),
        ):
            flask_app.preprocess_request()
            OAuthAuthorizePage(lambda: True).handle_page(
                PageContext(config=Config(), request=request)
            )

            assert 'action="/oauth-heute/authorize"' in response.get_data(as_text=True)

    @pytest.mark.usefixtures("clean_redis", "valid_transaction", "valid_csrf_token")
    def test_redirects_with_code_once_confirmed(
        self, flask_app: Flask, registered_client_id: str
    ) -> None:
        with flask_app.test_request_context(
            method="POST", data=_authorize_request(client_id=registered_client_id, state="xyz")
        ):
            flask_app.preprocess_request()
            with UserContext(_SESSION_USER, UserPermissions({}, {}, {}, [])):
                OAuthAuthorizePage(lambda: True).handle_page(
                    PageContext(config=Config(), request=request)
                )

            assert response.status_code == 200
            target_url = _extract_redirect_target(response.get_data(as_text=True))

        parts = urlsplit(target_url)
        assert f"{parts.scheme}://{parts.netloc}{parts.path}" == _REDIRECT_URI
        query = parse_qs(parts.query)
        assert query["state"] == ["xyz"]
        assert query["code"][0]

    @pytest.mark.usefixtures("clean_redis")
    @pytest.mark.parametrize(
        "submission",
        [
            pytest.param({}, id="approve"),
            pytest.param({"deny": "Deny"}, id="deny"),
        ],
    )
    def test_rejects_post_without_a_valid_csrf_token(
        self, flask_app: Flask, registered_client_id: str, submission: dict[str, str]
    ) -> None:
        # Both buttons submit the form, so neither may be answered without a
        # token. Only holds under a login session: check_csrf_token() passes
        # anything sent without one (LoggedInNobody).
        with flask_app.test_request_context(
            method="POST", data=_authorize_request(client_id=registered_client_id, **submission)
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

    @pytest.mark.usefixtures("valid_transaction", "valid_csrf_token")
    def test_redirects_with_access_denied_when_denied(
        self, flask_app: Flask, registered_client_id: str
    ) -> None:
        with flask_app.test_request_context(
            method="POST",
            data=_authorize_request(client_id=registered_client_id, state="xyz", deny="Deny"),
        ):
            flask_app.preprocess_request()
            with UserContext(_SESSION_USER, UserPermissions({}, {}, {}, [])):
                OAuthAuthorizePage(lambda: True).handle_page(
                    PageContext(config=Config(), request=request)
                )

            assert response.status_code == 200
            target_url = _extract_redirect_target(response.get_data(as_text=True))

        parts = urlsplit(target_url)
        assert f"{parts.scheme}://{parts.netloc}{parts.path}" == _REDIRECT_URI
        query = parse_qs(parts.query)
        assert query["error"] == ["access_denied"]
        assert query["state"] == ["xyz"]
        assert "code" not in query

    @pytest.mark.usefixtures("clean_redis", "valid_transaction", "valid_csrf_token")
    def test_preserves_existing_query_params_on_redirect_uri(self, flask_app: Flask) -> None:
        redirect_uri = f"{_REDIRECT_URI}?foo=bar"
        with get_client_store() as store:
            registration = store.register([redirect_uri], None)
        assert registration.is_ok()
        with flask_app.test_request_context(
            method="POST",
            data=_authorize_request(client_id=registration.ok.client_id, redirect_uri=redirect_uri),
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

    @pytest.mark.usefixtures("clean_redis", "valid_transaction", "valid_csrf_token")
    def test_redirect_page_is_not_an_http_redirect(
        self, flask_app: Flask, registered_client_id: str
    ) -> None:
        # Regression test: an HTTP 3xx here would carry the site's
        # form-action CSP over onto this cross-origin hop, and Chrome (unlike
        # Firefox) enforces that directive against redirects resulting from
        # a form submission -- blocking the navigation to redirect_uri since
        # it's necessarily a different origin (the OAuth client's callback).
        with flask_app.test_request_context(
            method="POST", data=_authorize_request(client_id=registered_client_id)
        ):
            flask_app.preprocess_request()
            with UserContext(_SESSION_USER, UserPermissions({}, {}, {}, [])):
                OAuthAuthorizePage(lambda: True).handle_page(
                    PageContext(config=Config(), request=request)
                )

            assert response.status_code == 200
            body = response.get_data(as_text=True)
            assert 'http-equiv="refresh"' in body

    @pytest.mark.usefixtures("valid_csrf_token")
    def test_shows_consent_page_again_when_not_confirmed(
        self, flask_app: Flask, registered_client_id: str
    ) -> None:
        # No valid_transaction fixture and no _transid in the submission, so
        # the real check fails it: a replayed or expired form submission.
        with flask_app.test_request_context(
            method="POST", data=_authorize_request(client_id=registered_client_id)
        ):
            flask_app.preprocess_request()
            with UserContext(_SESSION_USER, UserPermissions({}, {}, {}, [])):
                OAuthAuthorizePage(lambda: True).handle_page(
                    PageContext(config=Config(), request=request)
                )

            assert response.status_code == 200
            assert "<form" in response.get_data(as_text=True)

    @pytest.mark.parametrize(
        "overrides",
        [
            pytest.param({"redirect_uri": None}, id="redirect_uri-missing"),
            # The dangerous scheme is a regression test: redirect_uri ends up
            # in a href/content attribute on the redirect page, and
            # HTML-escaping alone doesn't stop a javascript: URI from executing
            # if that link is followed.
            pytest.param(
                {"redirect_uri": "javascript:alert(document.cookie)"},
                id="redirect_uri-dangerous-scheme",
            ),
            pytest.param({"client_id": None}, id="client_id-missing"),
            pytest.param({"client_id": "never-registered-client"}, id="client_id-unknown"),
            pytest.param(
                {"redirect_uri": "https://attacker.example/callback"},
                id="redirect_uri-not-registered",
            ),
        ],
    )
    def test_answers_400_without_redirecting(
        self, flask_app: Flask, registered_client_id: str, overrides: dict[str, str | None]
    ) -> None:
        # RFC 6749 section 4.1.2.1: until redirect_uri and client_id are both
        # known good, an unknown client's redirect_uri isn't trustworthy, so
        # the error must not be redirected anywhere.
        with flask_app.test_request_context(
            query_string=_authorize_request(**{"client_id": registered_client_id, **overrides})
        ):
            flask_app.preprocess_request()
            OAuthAuthorizePage(lambda: True).handle_page(
                PageContext(config=Config(), request=request)
            )

            assert response.status_code == 400

    @pytest.mark.parametrize(
        "overrides, error",
        [
            pytest.param({"response_type": None}, "invalid_request", id="response_type-missing"),
            pytest.param(
                {"response_type": "token"},
                "unsupported_response_type",
                id="response_type-not-code",
            ),
            pytest.param({"code_challenge": None}, "invalid_request", id="code_challenge-missing"),
            pytest.param(
                {"code_challenge_method": None},
                "invalid_request",
                id="code_challenge_method-missing",
            ),
            pytest.param(
                {"code_challenge_method": "plain"},
                "invalid_request",
                id="code_challenge_method-plain",
            ),
            # Rejected rather than downscoped: that beats letting the client
            # discover the gap on its first write.
            pytest.param({"scope": "read mcp"}, "invalid_scope", id="scope-unknown"),
        ],
    )
    def test_redirects_with_an_error(
        self,
        flask_app: Flask,
        registered_client_id: str,
        overrides: dict[str, str | None],
        error: str,
    ) -> None:
        # Once redirect_uri and client_id are known good, the client is told by
        # redirect (RFC 6749 section 4.1.2.1), with state echoed back so it can
        # match the answer to its request.
        with flask_app.test_request_context(
            query_string=_authorize_request(
                client_id=registered_client_id, state="xyz", **overrides
            )
        ):
            flask_app.preprocess_request()
            OAuthAuthorizePage(lambda: True).handle_page(
                PageContext(config=Config(), request=request)
            )

            assert response.status_code == 200
            target_url = _extract_redirect_target(response.get_data(as_text=True))

        query = parse_qs(urlsplit(target_url).query)
        assert query["error"] == [error]
        assert query["state"] == ["xyz"]

    @pytest.mark.parametrize(
        "overrides, reason",
        [
            pytest.param(
                {"client_id": "never-registered-client"},
                "unknown client_id",
                id="client_id-unknown",
            ),
            pytest.param(
                {"redirect_uri": "https://attacker.example/callback"},
                "redirect_uri not registered for client_id",
                id="redirect_uri-not-registered",
            ),
            # The reason names the scope refused: a report about a scope we
            # don't have is only actionable with it.
            pytest.param({"scope": "read mcp"}, "unknown scope: mcp", id="scope-unknown"),
        ],
    )
    def test_logs_a_security_event_for_what_a_broken_client_would_not_send(
        self,
        flask_app: Flask,
        security_log: MagicMock,
        registered_client_id: str,
        overrides: dict[str, str | None],
        reason: str,
    ) -> None:
        # A client that read either metadata document cannot name a client_id,
        # redirect_uri or scope this site does not have, so these are attempts
        # at something rather than the client bugs the other rejections are.
        with flask_app.test_request_context(
            query_string=_authorize_request(**{"client_id": registered_client_id, **overrides})
        ):
            flask_app.preprocess_request()
            OAuthAuthorizePage(lambda: True).handle_page(
                PageContext(config=Config(), request=request)
            )

        assert _logged_reason(security_log) == reason

    def test_returns_404_when_disabled(self, flask_app: Flask) -> None:
        # Answered before any parameter is looked at, so the request needs none.
        with flask_app.test_request_context(query_string=_authorize_request(client_id=None)):
            flask_app.preprocess_request()
            OAuthAuthorizePage(lambda: False).handle_page(
                PageContext(config=Config(), request=request)
            )

            assert response.status_code == 404

    @pytest.mark.usefixtures("clean_redis", "valid_transaction", "valid_csrf_token")
    def test_approve_persists_the_issued_code_bound_to_the_request(
        self, flask_app: Flask, registered_client_id: str
    ) -> None:
        with flask_app.test_request_context(
            method="POST",
            data=_authorize_request(
                client_id=registered_client_id,
                scope="read",
                resource="https://host/mysite/check_mk/mcp",
                code_challenge="foobar",
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
            redirect_uri=_REDIRECT_URI,
            scope="read",
            resource="https://host/mysite/check_mk/mcp",
            code_challenge="foobar",
        )

    @pytest.mark.usefixtures("clean_redis", "valid_transaction", "valid_csrf_token")
    def test_approve_binds_the_normalized_scope(
        self, flask_app: Flask, registered_client_id: str
    ) -> None:
        # A client asking to write is granted read as well -- one grant, one
        # spelling, decided here rather than at redemption.
        with flask_app.test_request_context(
            method="POST", data=_authorize_request(client_id=registered_client_id, scope="write")
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

    @pytest.mark.usefixtures("clean_redis", "valid_transaction", "valid_csrf_token")
    @pytest.mark.parametrize(
        "requested_scope",
        [
            pytest.param(None, id="absent"),
            pytest.param("   ", id="blank"),
        ],
    )
    def test_approve_without_scope_binds_the_default_scope(
        self, flask_app: Flask, registered_client_id: str, requested_scope: str | None
    ) -> None:
        with flask_app.test_request_context(
            method="POST",
            data=_authorize_request(client_id=registered_client_id, scope=requested_scope),
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

    @pytest.mark.usefixtures("clean_redis", "valid_transaction", "valid_csrf_token")
    def test_deny_persists_nothing(self, flask_app: Flask, registered_client_id: str) -> None:
        with flask_app.test_request_context(
            method="POST", data=_authorize_request(client_id=registered_client_id, deny="Deny")
        ):
            flask_app.preprocess_request()
            with UserContext(_SESSION_USER, UserPermissions({}, {}, {}, [])):
                OAuthAuthorizePage(lambda: True).handle_page(
                    PageContext(config=Config(), request=request)
                )

        assert get_redis_client().keys() == []

    @pytest.mark.usefixtures("clean_redis", "valid_transaction", "valid_csrf_token")
    def test_no_code_is_issued_when_the_store_is_unavailable(
        self, flask_app: Flask, registered_client_id: str
    ) -> None:
        with flask_app.test_request_context(
            method="POST", data=_authorize_request(client_id=registered_client_id, state="xyz")
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

    @pytest.mark.usefixtures("clean_redis", "valid_transaction", "valid_csrf_token")
    def test_logs_the_exception_when_the_store_is_unavailable(
        self, flask_app: Flask, caplog: pytest.LogCaptureFixture, registered_client_id: str
    ) -> None:
        # A store outage is nobody's attempt at anything, so it is not a
        # security event: this log entry, with the traceback, is the only
        # record of why no code was issued.
        with flask_app.test_request_context(
            method="POST", data=_authorize_request(client_id=registered_client_id)
        ):
            flask_app.preprocess_request()
            with (
                UserContext(_SESSION_USER, UserPermissions({}, {}, {}, [])),
                disable_redis(),
                caplog.at_level(logging.ERROR, logger="cmk.web"),
            ):
                OAuthAuthorizePage(lambda: True).handle_page(
                    PageContext(config=Config(), request=request)
                )

        [logged] = [record for record in caplog.records if record.name == "cmk.web"]
        assert logged.exc_info is not None

    @pytest.mark.usefixtures("clean_redis", "valid_transaction", "valid_csrf_token")
    def test_treats_a_request_timeout_as_a_store_failure(
        self, flask_app: Flask, mocker: MockerFixture, registered_client_id: str
    ) -> None:
        # A timeout inside store() takes the store-outage path, not the framework's handling.
        mocker.patch.object(AuthCodeStore, "store", side_effect=MKTimeout)
        with flask_app.test_request_context(
            method="POST", data=_authorize_request(client_id=registered_client_id)
        ):
            flask_app.preprocess_request()
            with UserContext(_SESSION_USER, UserPermissions({}, {}, {}, [])):
                OAuthAuthorizePage(lambda: True).handle_page(
                    PageContext(config=Config(), request=request)
                )

            target_url = _extract_redirect_target(response.get_data(as_text=True))

        assert parse_qs(urlsplit(target_url).query)["error"] == ["server_error"]
