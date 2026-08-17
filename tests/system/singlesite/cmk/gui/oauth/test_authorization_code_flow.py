#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""System-level tests for the RFC 6749 + PKCE authorization-code flow.

Walks the whole flow over real HTTP against a running site -- dynamic client
registration, the authenticated consent screen, and the token exchange --
which the Flask-test-client unit suite (tests/unit/cmk/gui/oauth/test_authorize.py)
cannot exercise: real Apache routing, the real login-session cookie, and real
CSRF (_transid) wiring all have to work together here.

Rejection-path coverage (missing/invalid params) is intentionally left to that
unit suite; this file mostly only covers the happy path and the user-denies
path. The one deliberate exception is client_id/redirect_uri validation
against the registered-client store: that's a security boundary (rejecting
requests for unregistered clients or mismatched redirect_uris) worth proving
holds over real HTTP, not just through the Flask test client, so it gets its
own narrow coverage here too.

Enabling the MCP server -- the only current oauth.registration.register() caller -- is
handled by the ``mcp_enabled_site`` fixture in conftest.py.
"""

import base64
import hashlib
import logging
import secrets
from urllib.parse import parse_qs, urlsplit

import pytest
import requests
from bs4 import BeautifulSoup, Tag

from tests.testlib.site import Site
from tests.testlib.web_session import CMKWebSession

_REGISTRATION_ENDPOINT_PATH = "oauth_client_registration.py"
_AUTHORIZE_ENDPOINT_PATH = "oauth_authorize.py"
_TOKEN_ENDPOINT_PATH = "oauth_token.py"
_REDIRECT_URI = "https://client.example.com/callback"

logger = logging.getLogger(__name__)


def _register_client(site: Site) -> str:
    """RFC 7591 dynamic client registration; returns the issued client_id."""
    url = site.internal_url + _REGISTRATION_ENDPOINT_PATH
    response = requests.post(
        url,
        json={"redirect_uris": [_REDIRECT_URI], "client_name": "Integration test client"},
        timeout=30,
    )
    logger.info("POST %s -> %d", url, response.status_code)
    assert response.status_code == 201
    client_id = response.json()["client_id"]
    assert isinstance(client_id, str) and client_id
    return client_id


def _make_pkce_pair() -> tuple[str, str]:
    """A real RFC 7636 S256 (code_verifier, code_challenge) pair."""
    code_verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    code_challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return code_verifier, code_challenge


def _get_consent_page(
    web: CMKWebSession,
    *,
    client_id: str,
    code_challenge: str,
    state: str,
    redirect_uri: str = _REDIRECT_URI,
    expected_code: int = 200,
) -> requests.Response:
    return web.get(
        _AUTHORIZE_ENDPOINT_PATH,
        params={
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
            "state": state,
        },
        expected_code=expected_code,
    )


def _hidden_form_fields(html_text: str) -> dict[str, str]:
    """All hidden <input> values inside the consent page's <form>.

    Covers the echoed request params (html.hidden_fields()) plus the
    form-machinery fields added by html.form_context() (_transid, _csrf_token,
    filled_in) -- everything the real POST needs to pass CSRF/transaction
    validation, without hardcoding those field names here.
    """
    form = BeautifulSoup(html_text, "lxml").find("form")
    assert isinstance(form, Tag), "consent page did not render a <form>"
    fields: dict[str, str] = {}
    for field in form.find_all("input", type="hidden"):
        name = field.get("name")
        value = field.get("value", "")
        assert isinstance(name, str)
        assert isinstance(value, str)
        fields[name] = value
    return fields


def _redirect_target(html_text: str) -> str:
    """The target URL out of the redirect-stub page's <meta refresh> tag."""
    meta = BeautifulSoup(html_text, "lxml").find("meta", attrs={"http-equiv": "refresh"})
    assert isinstance(meta, Tag), "redirect page did not render a <meta refresh> tag"
    content = meta.get("content")
    assert isinstance(content, str)
    _, _, target = content.partition("url=")
    assert target, f"no 'url=' in meta refresh content: {content!r}"
    return target


@pytest.mark.skip_if_edition("community", "cloud")
def test_full_authorization_code_flow_with_pkce(mcp_enabled_site: Site, web: CMKWebSession) -> None:
    """Register a client, run the consent screen, and redeem the issued code for a token."""
    client_id = _register_client(mcp_enabled_site)
    code_verifier, code_challenge = _make_pkce_pair()
    state = secrets.token_urlsafe(8)

    consent_page = _get_consent_page(
        web, client_id=client_id, code_challenge=code_challenge, state=state
    )
    hidden_fields = _hidden_form_fields(consent_page.text)

    approval = web.post(
        _AUTHORIZE_ENDPOINT_PATH,
        data={**hidden_fields, "_authorize": "Authorize"},
    )
    query = parse_qs(urlsplit(_redirect_target(approval.text)).query)
    assert query["state"] == [state]
    code = query["code"][0]

    token_url = mcp_enabled_site.internal_url + _TOKEN_ENDPOINT_PATH
    token_response = requests.post(
        token_url,
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": _REDIRECT_URI,
            "client_id": client_id,
            "code_verifier": code_verifier,
        },
        timeout=30,
    )
    logger.info("POST %s -> %d", token_url, token_response.status_code)
    assert token_response.status_code == 200
    token_body = token_response.json()
    assert token_body["access_token"]
    assert token_body["token_type"] == "Bearer"


@pytest.mark.skip_if_edition("community", "cloud")
def test_authorize_deny_redirects_with_access_denied(
    mcp_enabled_site: Site, web: CMKWebSession
) -> None:
    """Denying consent redirects back with error=access_denied, not a code."""
    client_id = _register_client(mcp_enabled_site)
    _, code_challenge = _make_pkce_pair()
    state = secrets.token_urlsafe(8)

    consent_page = _get_consent_page(
        web, client_id=client_id, code_challenge=code_challenge, state=state
    )
    hidden_fields = _hidden_form_fields(consent_page.text)

    denial = web.post(
        _AUTHORIZE_ENDPOINT_PATH,
        data={**hidden_fields, "_deny": "Deny"},
    )
    query = parse_qs(urlsplit(_redirect_target(denial.text)).query)
    assert query["error"] == ["access_denied"]
    assert query["state"] == [state]
    assert "code" not in query


@pytest.mark.skip_if_edition("community", "cloud")
def test_authorize_returns_400_for_unknown_client_id(
    mcp_enabled_site: Site, web: CMKWebSession
) -> None:
    """A client_id that was never dynamically registered must not reach the consent screen."""
    _, code_challenge = _make_pkce_pair()
    state = secrets.token_urlsafe(8)

    _get_consent_page(
        web,
        client_id="never-registered-client",
        code_challenge=code_challenge,
        state=state,
        expected_code=400,
    )


@pytest.mark.skip_if_edition("community", "cloud")
def test_authorize_returns_400_for_redirect_uri_not_registered_to_client(
    mcp_enabled_site: Site, web: CMKWebSession
) -> None:
    """redirect_uri must be one of the client's own registered URIs, not just well-formed."""
    client_id = _register_client(mcp_enabled_site)
    _, code_challenge = _make_pkce_pair()
    state = secrets.token_urlsafe(8)

    _get_consent_page(
        web,
        client_id=client_id,
        code_challenge=code_challenge,
        state=state,
        redirect_uri="https://attacker.example/callback",
        expected_code=400,
    )
