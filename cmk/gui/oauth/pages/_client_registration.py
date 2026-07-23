#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import http.client as http_client
from collections.abc import Callable
from typing import override

from pydantic import ValidationError

from cmk.gui.http import request, response
from cmk.gui.oauth import client_store
from cmk.gui.oauth.pages._models import (
    OAuthClientRegistrationErrorResponse,
    OAuthClientRegistrationRequest,
    OAuthClientRegistrationResponse,
)
from cmk.gui.oauth.store.client_store import ClientRegistrationLimitExceededError
from cmk.gui.pages import Page, PageContext, PageResult


def _registration_error(exc: ValidationError) -> OAuthClientRegistrationErrorResponse:
    error = exc.errors()[0]
    field = error["loc"][0] if error["loc"] else "redirect_uris"
    code = "invalid_redirect_uri" if field == "redirect_uris" else "invalid_client_metadata"
    return OAuthClientRegistrationErrorResponse(
        error=code, error_description=error["msg"].removeprefix("Value error, ")
    )


class OAuthClientRegistrationPage(Page):
    """RFC 7591 dynamic client registration endpoint for this site.

    Accessed unauthenticated, referenced via the "registration_endpoint" field
    of the RFC 8414 authorization server metadata document. Returns 404 while
    no OAuth-consuming feature is enabled for the site (the enabled predicate
    is injected at registration).

    Validates the shape of the submitted client metadata (see
    OAuthClientRegistrationRequest) and persists it via
    cmk.gui.oauth.client_store(). redirect_uris is echoed back from
    the request body -- see OAuthClientRegistrationResponse's docstring for
    why that's required, not optional polish. Validation failures and a
    reached registration limit are both reported per RFC 7591 section 3.2.2
    (JSON error/error_description body), not just a bare status code.
    """

    def __init__(self, enabled: Callable[[], bool]) -> None:
        self._enabled = enabled

    @override
    def page(self, ctx: PageContext) -> PageResult:
        if not self._enabled():
            response.status_code = http_client.NOT_FOUND
            return None

        if request.request_method != "POST":
            response.status_code = http_client.METHOD_NOT_ALLOWED
            return None

        try:
            body = OAuthClientRegistrationRequest.model_validate(request.get_json(silent=True))
        except ValidationError as exc:
            response.status_code = http_client.BAD_REQUEST
            response.set_content_type("application/json")
            response.set_data(_registration_error(exc).model_dump_json())
            return None

        try:
            registration = client_store().register(body.redirect_uris, body.client_name)
        except ClientRegistrationLimitExceededError:
            response.status_code = http_client.BAD_REQUEST
            response.set_content_type("application/json")
            response.set_data(
                OAuthClientRegistrationErrorResponse(
                    error="invalid_client_metadata",
                    error_description="client registration limit reached",
                ).model_dump_json()
            )
            return None

        response.status_code = http_client.CREATED
        response.set_content_type("application/json")
        response.set_data(
            OAuthClientRegistrationResponse(
                client_id=registration.client_id,
                redirect_uris=body.redirect_uris,
                client_name=body.client_name,
            ).model_dump_json()
        )
        return None
