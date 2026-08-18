#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from datetime import datetime, timedelta, UTC

import pytest
import time_machine
from flask import Flask

from cmk.ccc.user import UserId
from cmk.gui.config import Config
from cmk.gui.http import request, response
from cmk.gui.oauth.pages._introspect import OAuthIntrospectPage
from cmk.gui.oauth.store.client_store import get_client_store
from cmk.gui.oauth.store.token_store import get_token_store
from cmk.gui.pages import PageContext
from cmk.gui.scopes import DEFAULT_SCOPE
from tests.testlib.gui.users import create_and_destroy_user

_FORM_CONTENT_TYPE = "application/x-www-form-urlencoded"
_TOKEN_TTL = timedelta(minutes=5)


@pytest.fixture(name="client_id")
def fixture_client_id(flask_app: Flask) -> str:
    with get_client_store() as store:
        registered = store.register(["https://client.example/callback"], None)
    assert registered.is_ok()
    return registered.ok.client_id


def _issue_token(user_id: UserId, client_id: str, expires_at: datetime) -> str:
    with get_token_store() as store:
        result = store.issue_token(
            user_id,
            expires_at=expires_at,
            resource=None,
            scope=DEFAULT_SCOPE,
            client_id=client_id,
        )
    assert result.is_ok()
    return result.ok


@pytest.mark.usefixtures("request_context")
class TestOAuthIntrospectPage:
    def test_reports_a_valid_token_as_active(
        self, flask_app: Flask, with_user: tuple[UserId, str], client_id: str
    ) -> None:
        user_id, _password = with_user
        expires_at = datetime.now(UTC) + _TOKEN_TTL
        token = _issue_token(user_id, client_id, expires_at)
        with flask_app.test_request_context(method="POST", data={"token": token}):
            flask_app.preprocess_request()
            OAuthIntrospectPage(lambda: True).handle_page(
                PageContext(config=Config(), request=request)
            )

            assert response.status_code == 200
            assert response.json == {"active": True, "exp": int(expires_at.timestamp())}

    def test_reports_an_expired_token_as_inactive(
        self, flask_app: Flask, with_user: tuple[UserId, str], client_id: str
    ) -> None:
        user_id, _password = with_user
        token = _issue_token(user_id, client_id, datetime.now(UTC) + _TOKEN_TTL)
        with (
            time_machine.travel(datetime.now(UTC) + _TOKEN_TTL + timedelta(minutes=1)),
            flask_app.test_request_context(method="POST", data={"token": token}),
        ):
            flask_app.preprocess_request()
            OAuthIntrospectPage(lambda: True).handle_page(
                PageContext(config=Config(), request=request)
            )

            assert response.status_code == 200
            assert response.json == {"active": False}

    @pytest.mark.parametrize(
        "token",
        [
            pytest.param("cmko1.tXWlEdCFwyWyLLD9AoSvBaLl6HXhFsEEJ4kUcgQvzKY", id="never_issued"),
            pytest.param("not-a-token-at-all", id="not_shaped_like_a_token"),
        ],
    )
    def test_reports_a_token_this_site_never_issued_as_inactive(
        self, flask_app: Flask, token: str
    ) -> None:
        with flask_app.test_request_context(method="POST", data={"token": token}):
            flask_app.preprocess_request()
            OAuthIntrospectPage(lambda: True).handle_page(
                PageContext(config=Config(), request=request)
            )

            assert response.status_code == 200
            assert response.json == {"active": False}

    def test_reports_a_token_of_a_deleted_user_as_inactive(
        self, flask_app: Flask, load_config: Config, client_id: str
    ) -> None:
        # Deleting a user does not touch their tokens, so the token itself is
        # still unexpired here. Answering "active" would send the caller into a
        # REST API request that authentication rejects.
        with create_and_destroy_user(config=load_config) as (user_id, _password):
            token = _issue_token(user_id, client_id, datetime.now(UTC) + _TOKEN_TTL)

        with flask_app.test_request_context(method="POST", data={"token": token}):
            flask_app.preprocess_request()
            OAuthIntrospectPage(lambda: True).handle_page(
                PageContext(config=Config(), request=request)
            )

            assert response.status_code == 200
            assert response.json == {"active": False}

    def test_reports_a_token_of_a_locked_user_as_inactive(
        self, flask_app: Flask, load_config: Config, client_id: str
    ) -> None:
        with create_and_destroy_user(custom_attrs={"locked": True}, config=load_config) as (
            user_id,
            _password,
        ):
            token = _issue_token(user_id, client_id, datetime.now(UTC) + _TOKEN_TTL)
            with flask_app.test_request_context(method="POST", data={"token": token}):
                flask_app.preprocess_request()
                OAuthIntrospectPage(lambda: True).handle_page(
                    PageContext(config=Config(), request=request)
                )

                assert response.status_code == 200
                assert response.json == {"active": False}

    @pytest.mark.parametrize("data", [{}, {"token": ""}], ids=["missing", "empty"])
    def test_rejects_a_request_without_a_token(
        self, flask_app: Flask, data: dict[str, str]
    ) -> None:
        with flask_app.test_request_context(
            method="POST", data=data, content_type=_FORM_CONTENT_TYPE
        ):
            flask_app.preprocess_request()
            OAuthIntrospectPage(lambda: True).handle_page(
                PageContext(config=Config(), request=request)
            )

            assert response.status_code == 400
            assert response.json == {"error": "invalid_request"}

    def test_ignores_a_token_in_the_query_string(
        self, flask_app: Flask, with_user: tuple[UserId, str], client_id: str
    ) -> None:
        user_id, _password = with_user
        token = _issue_token(user_id, client_id, datetime.now(UTC) + _TOKEN_TTL)
        with flask_app.test_request_context(
            f"/oauth_introspect.py?token={token}", method="POST", content_type=_FORM_CONTENT_TYPE
        ):
            flask_app.preprocess_request()
            OAuthIntrospectPage(lambda: True).handle_page(
                PageContext(config=Config(), request=request)
            )

            assert response.status_code == 400
            assert response.json == {"error": "invalid_request"}

    def test_returns_405_when_method_is_not_post(self, flask_app: Flask) -> None:
        with flask_app.test_request_context(method="GET"):
            flask_app.preprocess_request()
            OAuthIntrospectPage(lambda: True).handle_page(
                PageContext(config=Config(), request=request)
            )

            assert response.status_code == 405

    def test_rejects_a_non_form_content_type(self, flask_app: Flask) -> None:
        with flask_app.test_request_context(
            method="POST",
            data='{"token": "cmko1.tXWlEdCFwyWyLLD9AoSvBaLl6HXhFsEEJ4kUcgQvzKY"}',
            content_type="application/json",
        ):
            flask_app.preprocess_request()
            OAuthIntrospectPage(lambda: True).handle_page(
                PageContext(config=Config(), request=request)
            )

            assert response.status_code == 400
            assert response.json == {"error": "invalid_request"}

    def test_returns_404_when_disabled(self, flask_app: Flask) -> None:
        with flask_app.test_request_context(
            method="POST", data={"token": "cmko1.tXWlEdCFwyWyLLD9AoSvBaLl6HXhFsEEJ4kUcgQvzKY"}
        ):
            flask_app.preprocess_request()
            OAuthIntrospectPage(lambda: False).handle_page(
                PageContext(config=Config(), request=request)
            )

            assert response.status_code == 404
