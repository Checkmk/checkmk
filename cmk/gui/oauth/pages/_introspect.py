#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import http.client as http_client
from collections.abc import Callable
from typing import override

from cmk.gui.http import request, response
from cmk.gui.oauth.active_token import active_token
from cmk.gui.oauth.pages._models import OAuthTokenErrorResponse, OAuthTokenIntrospectionResponse
from cmk.gui.pages import Page, PageContext, PageResult

_FORM_CONTENT_TYPE = "application/x-www-form-urlencoded"


def _error() -> None:
    """RFC 7662 section 2.3: a malformed request gets an RFC 6749 section 5.2 error."""
    response.status_code = http_client.BAD_REQUEST
    response.set_content_type("application/json")
    response.set_data(OAuthTokenErrorResponse(error="invalid_request").model_dump_json())


class OAuthIntrospectPage(Page):
    """RFC 7662 token introspection endpoint for this site.

    Reports whether an access token is still usable -- unexpired, with a user
    that still exists and isn't locked (see cmk.gui.oauth.active_token), the
    same bar cmk.gui.auth applies. Deliberately unauthenticated, deviating
    from RFC 7662 section 2.1's MUST-protect: only reachable over the
    loopback trust boundary, and tokens are 256-bit secrets, so a
    guessed-token query leads nowhere. Not advertised in the RFC 8414
    metadata document and not proxied publicly (see _oauth_well_known.py).
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

        if request.mimetype != _FORM_CONTENT_TYPE:
            _error()
            return None

        # The token travels in the entity-body only (RFC 7662 section 2.1)
        if (token := request.form.get("token")) is None or token == "":
            _error()
            return None

        record = active_token(token)
        response.set_content_type("application/json")
        response.set_data(
            OAuthTokenIntrospectionResponse(
                active=record is not None,
                exp=int(record.expires_at.timestamp()) if record is not None else None,
            ).model_dump_json()
        )
        return None
