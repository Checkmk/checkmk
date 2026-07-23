#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import urllib.parse
from typing import Annotated

from pydantic import BaseModel, Field, field_validator


class OAuthAuthorizationServerMetadata(BaseModel):
    """RFC 8414 authorization server metadata document.

    response_types_supported, grant_types_supported,
    token_endpoint_auth_methods_supported and code_challenge_methods_supported
    are not just decorative: an MCP client checking for PKCE support
    (mandatory in its OAuth 2.1 flow) before treating this as a usable
    authorization server needs code_challenge_methods_supported present, or
    it silently falls back to guessing a registration endpoint instead of
    using ours.
    """

    issuer: str
    authorization_endpoint: str
    registration_endpoint: str
    token_endpoint: str
    response_types_supported: list[str] = ["code"]
    grant_types_supported: list[str] = ["authorization_code"]
    token_endpoint_auth_methods_supported: list[str] = ["none"]
    code_challenge_methods_supported: list[str] = ["S256"]


class OAuthClientRegistrationRequest(BaseModel):
    """RFC 7591 dynamic client registration request body."""

    redirect_uris: list[Annotated[str, Field(max_length=2048)]] = Field(min_length=1, max_length=10)
    client_name: str | None = Field(default=None, max_length=200)

    @field_validator("redirect_uris")
    @classmethod
    def _reject_disallowed_schemes(cls, redirect_uris: list[str]) -> list[str]:
        for uri in redirect_uris:
            if urllib.parse.urlsplit(uri).scheme not in ("http", "https"):
                raise ValueError(f"redirect_uri must use http or https scheme: {uri}")
        return redirect_uris


class OAuthClientRegistrationResponse(BaseModel):
    """RFC 7591 dynamic client registration response.

    Echoes back the client's own submitted metadata: RFC 7591 section 3.2.1
    requires the response to include all registered metadata, and MCP
    clients (observed with Claude Code) parse the response into a
    client-info model that requires redirect_uris specifically -- without
    it, the client silently drops the connection attempt right after
    registering, with no further requests to explain why.
    """

    client_id: str
    redirect_uris: list[str] = []
    client_name: str | None = None


class OAuthClientRegistrationErrorResponse(BaseModel):
    """RFC 7591 section 3.2.2 client registration error response."""

    error: str
    error_description: str


class OAuthTokenResponse(BaseModel):
    """RFC 6749 section 5.1 access token response."""

    access_token: str
    token_type: str = "Bearer"


class OAuthTokenErrorResponse(BaseModel):
    """RFC 6749 section 5.2 token endpoint error response.

    Serialized with exclude_none so the optional error_description is absent
    from the body rather than null: clients parse {"error": ...} strictly.
    """

    error: str
    error_description: str | None = None
