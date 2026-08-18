#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest
from flask import Flask

from cmk.gui.config import Config
from cmk.gui.http import request, response
from cmk.gui.oauth.pages._client_registration import OAuthClientRegistrationPage
from cmk.gui.oauth.store.client_store import get_client_store
from cmk.gui.pages import PageContext


@pytest.mark.usefixtures("request_context")
class TestOAuthClientRegistrationPage:
    def test_returns_client_id_when_enabled(self, flask_app: Flask) -> None:
        with flask_app.test_request_context(
            method="POST",
            json={
                "redirect_uris": ["https://client.example/callback"],
                "client_name": "Example MCP Client",
            },
        ):
            flask_app.preprocess_request()
            OAuthClientRegistrationPage(lambda: True).handle_page(
                PageContext(config=Config(), request=request)
            )

            assert response.status_code == 201
            assert isinstance(response.json, dict)
            client_id = response.json["client_id"]
            assert isinstance(client_id, str)
            assert client_id

    def test_response_echoes_all_submitted_client_metadata(self, flask_app: Flask) -> None:
        # Extend this payload as more RFC 7591 client metadata fields get modeled --
        # section 3.2.1 requires the response to include all registered (accepted)
        # metadata, not just redirect_uris.
        submitted = {
            "redirect_uris": ["https://client.example/callback"],
            "client_name": "Example MCP Client",
        }
        with flask_app.test_request_context(method="POST", json=submitted):
            flask_app.preprocess_request()
            OAuthClientRegistrationPage(lambda: True).handle_page(
                PageContext(config=Config(), request=request)
            )

            assert response.status_code == 201
            assert isinstance(response.json, dict)
            for field, value in submitted.items():
                assert response.json[field] == value

    def test_returns_different_client_id_on_each_call(self, flask_app: Flask) -> None:
        with flask_app.test_request_context(
            method="POST", json={"redirect_uris": ["https://client.example/callback"]}
        ):
            flask_app.preprocess_request()
            OAuthClientRegistrationPage(lambda: True).handle_page(
                PageContext(config=Config(), request=request)
            )
            assert isinstance(response.json, dict)
            first_client_id = response.json["client_id"]

            OAuthClientRegistrationPage(lambda: True).handle_page(
                PageContext(config=Config(), request=request)
            )
            assert isinstance(response.json, dict)
            second_client_id = response.json["client_id"]

        assert first_client_id != second_client_id

    def test_returns_404_when_disabled(self, flask_app: Flask) -> None:
        with flask_app.test_request_context(method="POST"):
            flask_app.preprocess_request()
            OAuthClientRegistrationPage(lambda: False).handle_page(
                PageContext(config=Config(), request=request)
            )

            assert response.status_code == 404

    def test_returns_405_when_method_is_not_post(self, flask_app: Flask) -> None:
        with flask_app.test_request_context(method="GET"):
            flask_app.preprocess_request()
            OAuthClientRegistrationPage(lambda: True).handle_page(
                PageContext(config=Config(), request=request)
            )

            assert response.status_code == 405

    def test_returns_400_when_no_body_is_sent(self, flask_app: Flask) -> None:
        with flask_app.test_request_context(method="POST"):
            flask_app.preprocess_request()
            OAuthClientRegistrationPage(lambda: True).handle_page(
                PageContext(config=Config(), request=request)
            )

            assert response.status_code == 400
            assert isinstance(response.json, dict)
            assert response.json["error"] == "invalid_redirect_uri"
            assert response.json["error_description"]

    def test_returns_400_when_redirect_uris_missing(self, flask_app: Flask) -> None:
        with flask_app.test_request_context(method="POST", json={}):
            flask_app.preprocess_request()
            OAuthClientRegistrationPage(lambda: True).handle_page(
                PageContext(config=Config(), request=request)
            )

            assert response.status_code == 400
            assert isinstance(response.json, dict)
            assert response.json["error"] == "invalid_redirect_uri"

    def test_returns_400_when_redirect_uris_empty(self, flask_app: Flask) -> None:
        with flask_app.test_request_context(method="POST", json={"redirect_uris": []}):
            flask_app.preprocess_request()
            OAuthClientRegistrationPage(lambda: True).handle_page(
                PageContext(config=Config(), request=request)
            )

            assert response.status_code == 400
            assert isinstance(response.json, dict)
            assert response.json["error"] == "invalid_redirect_uri"

    def test_returns_400_when_redirect_uri_scheme_is_not_http_or_https(
        self, flask_app: Flask
    ) -> None:
        with flask_app.test_request_context(
            method="POST", json={"redirect_uris": ["javascript:alert(1)"]}
        ):
            flask_app.preprocess_request()
            OAuthClientRegistrationPage(lambda: True).handle_page(
                PageContext(config=Config(), request=request)
            )

            assert response.status_code == 400
            assert isinstance(response.json, dict)
            assert response.json["error"] == "invalid_redirect_uri"
            assert "javascript:alert(1)" in response.json["error_description"]

    def test_returns_400_when_too_many_redirect_uris_are_submitted(self, flask_app: Flask) -> None:
        with flask_app.test_request_context(
            method="POST",
            json={"redirect_uris": [f"https://client.example/{i}" for i in range(11)]},
        ):
            flask_app.preprocess_request()
            OAuthClientRegistrationPage(lambda: True).handle_page(
                PageContext(config=Config(), request=request)
            )

            assert response.status_code == 400
            assert isinstance(response.json, dict)
            assert response.json["error"] == "invalid_redirect_uri"

    def test_returns_400_when_client_name_is_not_a_string(self, flask_app: Flask) -> None:
        with flask_app.test_request_context(
            method="POST",
            json={"redirect_uris": ["https://client.example/callback"], "client_name": 123},
        ):
            flask_app.preprocess_request()
            OAuthClientRegistrationPage(lambda: True).handle_page(
                PageContext(config=Config(), request=request)
            )

            assert response.status_code == 400
            assert isinstance(response.json, dict)
            assert response.json["error"] == "invalid_client_metadata"

    def test_registered_client_id_is_persisted(self, flask_app: Flask) -> None:
        with flask_app.test_request_context(
            method="POST",
            json={"redirect_uris": ["https://client.example/callback"]},
        ):
            flask_app.preprocess_request()
            OAuthClientRegistrationPage(lambda: True).handle_page(
                PageContext(config=Config(), request=request)
            )

            assert isinstance(response.json, dict)
            client_id = response.json["client_id"]

        with get_client_store() as store:
            assert store.get(client_id) is not None

    def test_returns_400_when_registration_limit_is_reached(self, flask_app: Flask) -> None:
        with get_client_store() as store:
            store._connection.executemany(
                """
                INSERT INTO clients (client_id, redirect_uris, client_name, registered_at)
                VALUES (?, '["https://client.example/callback"]', NULL, 0)
                """,
                [(f"limit-test-client-{i}",) for i in range(1000)],
            )

        with flask_app.test_request_context(
            method="POST",
            json={"redirect_uris": ["https://client.example/callback"]},
        ):
            flask_app.preprocess_request()
            OAuthClientRegistrationPage(lambda: True).handle_page(
                PageContext(config=Config(), request=request)
            )

            assert response.status_code == 400
            assert isinstance(response.json, dict)
            assert response.json["error"] == "invalid_client_metadata"

    def test_returns_400_when_a_redirect_uri_is_too_long(self, flask_app: Flask) -> None:
        with flask_app.test_request_context(
            method="POST",
            json={"redirect_uris": ["https://client.example/" + "a" * 2048]},
        ):
            flask_app.preprocess_request()
            OAuthClientRegistrationPage(lambda: True).handle_page(
                PageContext(config=Config(), request=request)
            )

            assert response.status_code == 400
            assert isinstance(response.json, dict)
            assert response.json["error"] == "invalid_redirect_uri"

    def test_returns_400_when_client_name_is_too_long(self, flask_app: Flask) -> None:
        with flask_app.test_request_context(
            method="POST",
            json={
                "redirect_uris": ["https://client.example/callback"],
                "client_name": "a" * 201,
            },
        ):
            flask_app.preprocess_request()
            OAuthClientRegistrationPage(lambda: True).handle_page(
                PageContext(config=Config(), request=request)
            )

            assert response.status_code == 400
            assert isinstance(response.json, dict)
            assert response.json["error"] == "invalid_client_metadata"
