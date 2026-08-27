#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import base64
import hashlib
import hmac
import http.client as http_client
import re
from collections.abc import Callable
from datetime import datetime, timedelta, UTC
from typing import Literal, override

from cmk.ccc.resulttype import Error, OK
from cmk.ccc.user import UserId
from cmk.gui.http import request, response
from cmk.gui.log import logger
from cmk.gui.oauth.pages._models import OAuthTokenErrorResponse, OAuthTokenResponse
from cmk.gui.oauth.store._auth_code_store import AuthCodeStore
from cmk.gui.oauth.store.token_store import get_token_store, UnknownClient
from cmk.gui.pages import Page, PageContext, PageResult
from cmk.gui.scopes import format_scopes, parse_scopes
from cmk.gui.utils.security_log_events import OAuthTokenFailureEvent
from cmk.utils.security_event import log_security_event

_FORM_CONTENT_TYPE = "application/x-www-form-urlencoded"

# The parameters this endpoint interprets. RFC 6749 section 3.2 forbids
# repeating request parameters, but it also requires unrecognized ones to be
# ignored, so the duplicate check deliberately covers only this set. Extend
# it before reading further parameters. Rejecting a repeated resource also
# rejects RFC 8707's multi-resource requests on purpose: a code binds
# exactly one resource here.
_KNOWN_PARAMS = ("grant_type", "code", "client_id", "code_verifier", "redirect_uri", "resource")

# RFC 7636 section 4.1: 43 to 128 characters from the unreserved set.
_CODE_VERIFIER_RE = re.compile(r"[A-Za-z0-9\-._~]{43,128}")

# Not tied to AuthCodeStore.AUTH_CODE_TTL (that's the short-lived code, this
# is the token it's redeemed for). Long-lived because permissions are
# re-checked on every request; a compromised token is bounded by that, not by
# its own expiry.
_ACCESS_TOKEN_TTL = timedelta(hours=48)

_TokenError = Literal["invalid_request", "unsupported_grant_type", "invalid_grant"]


def _error(error: _TokenError) -> None:
    """RFC 6749 section 5.2 error response: HTTP 400 with a JSON body."""
    response.status_code = http_client.BAD_REQUEST
    response.set_content_type("application/json")
    response.set_data(OAuthTokenErrorResponse(error=error).model_dump_json())


def _matches_challenge(code_verifier: str, code_challenge: str) -> bool:
    """RFC 7636 section 4.6: base64url(SHA256(ascii(code_verifier))), unpadded.

    Compared in bytes mode: the stored challenge is taken as the client sent
    it to the authorize endpoint, and str-mode compare_digest would raise on
    non-ASCII input instead of just not matching.
    """
    computed = base64.urlsafe_b64encode(
        hashlib.sha256(code_verifier.encode("ascii")).digest()
    ).rstrip(b"=")
    return hmac.compare_digest(computed, code_challenge.encode())


class OAuthTokenPage(Page):
    """RFC 6749 section 3.2 token endpoint for this site.

    Accessed unauthenticated, referenced via the "token_endpoint" field of the
    RFC 8414 authorization server metadata document. Returns 404 while no
    OAuth-consuming feature is enabled for the site (the enabled predicate is
    injected at registration).

    The request shape is validated (POST, form encoding, grant_type, required
    parameters, code_verifier syntax), authorization codes are redeemed
    single-use against the store the authorize endpoint fills, and every
    binding of the redeemed record is enforced: the PKCE S256 challenge, the
    client_id (which must still be registered), and redirect_uri/resource if
    sent. A scope parameter on the token request is ignored; the token's user
    and scope come only from the record, so the scope is the one the user
    approved rather than one the client picks at redemption. It is echoed back
    in the response body, so a client that asked for more than it got finds out
    here instead of on its first rejected write.
    Rejections follow the RFC 6749 section 5.2 error format. The returned
    access token is a real, store-backed token issued for the record's user
    (see cmk.gui.oauth.store.token_store).
    """

    def __init__(self, enabled: Callable[[], bool]) -> None:
        self._enabled = enabled

    @override
    def page(self, ctx: PageContext) -> PageResult:
        if not self._enabled():
            response.status_code = http_client.NOT_FOUND
            return None

        # RFC 6749 section 5.1/5.2: token endpoint responses carry tokens or
        # error details and MUST NOT be cached. Set up front to cover every
        # exit path below.
        response.headers["Cache-Control"] = "no-store"

        if request.request_method != "POST":
            response.status_code = http_client.METHOD_NOT_ALLOWED
            return None

        if request.mimetype != _FORM_CONTENT_TYPE:
            _error("invalid_request")
            return None

        # Token request parameters travel in the entity-body only (RFC 6749
        # section 4.1.3): request.form, never request.var, which would also
        # accept the query string and thereby leak the code and code_verifier
        # secrets into access logs. An empty value counts as absent
        # (section 3.2).
        form = request.form
        if any(len(form.getlist(name)) > 1 for name in _KNOWN_PARAMS):
            _error("invalid_request")
            return None

        grant_type = form.get("grant_type")
        if not grant_type:
            _error("invalid_request")
            return None
        if grant_type != "authorization_code":
            _error("unsupported_grant_type")
            return None

        # redirect_uri is deliberately not required here: OAuth 2.1
        # (section 10.2) removed it from the token request; it is only
        # enforced against the stored record if the client sends one.
        code = form.get("code")
        if not code or not form.get("client_id"):
            _error("invalid_request")
            return None

        # Absent and malformed count the same: the syntax check runs before
        # the code is consumed, so a bad request never burns a code.
        code_verifier = form.get("code_verifier")
        if code_verifier is None or _CODE_VERIFIER_RE.fullmatch(code_verifier) is None:
            _error("invalid_request")
            return None

        # The GETDEL behind consume() burns the code on this first touch, so
        # even concurrent redemption attempts yield at most one success.
        try:
            record = AuthCodeStore().consume(code)
        except Exception:
            # Deliberately also catches the GUI request timeout (MKTimeout):
            # the client should get the OAuth-level error response.
            # RFC 6749 section 5.2 defines no server_error code for the token
            # endpoint (unlike the authorize side), so a plain 500. The
            # security event only carries a static reason; the cause goes to
            # the log.
            logger.exception("failed to redeem OAuth authorization code")
            log_security_event(
                OAuthTokenFailureEvent(
                    reason="failed to redeem authorization code",
                    client_id=form.get("client_id"),
                    remote_ip=request.remote_ip,
                )
            )
            response.status_code = http_client.INTERNAL_SERVER_ERROR
            return None
        if record is None:
            _error("invalid_grant")
            return None

        if not _matches_challenge(code_verifier, record.code_challenge):
            # The code is already burned at this point, so a wrong verifier
            # costs the presenter the code: each code allows exactly one
            # verification attempt.
            _error("invalid_grant")
            return None

        if form.get("client_id") != record.client_id:
            # RFC 6749 section 4.1.3: the code must have been issued to the
            # client presenting it.
            _error("invalid_grant")
            return None

        # redirect_uri and resource are enforced only if sent: OAuth 2.1
        # (section 10.2) removed redirect_uri from the token request but
        # requires servers to keep verifying it for OAuth 2.0 clients that
        # still send it; resource follows the same if-sent rule (RFC 8707).
        if (redirect_uri := form.get("redirect_uri")) and redirect_uri != record.redirect_uri:
            _error("invalid_grant")
            return None
        if (resource := form.get("resource")) and resource != record.resource:
            _error("invalid_grant")
            return None

        # We assume that parse_scopes will be fine here, as we serialized the previously parsed
        # scopes into the AuthCodeStore ourselves. If it still goes wrong it's not a user error.
        granted_scopes = parse_scopes(record.scope)

        with get_token_store() as store:
            match store.issue_token(
                UserId(record.user_id),
                expires_at=datetime.now(UTC) + _ACCESS_TOKEN_TTL,
                resource=record.resource,
                scope=granted_scopes,
                client_id=record.client_id,
            ):
                case Error(UnknownClient()):
                    # The client was deleted after the code was issued. Its grants
                    # died with it (tokens.client_id is ON DELETE CASCADE), so the
                    # code must not become a token either.
                    _error("invalid_grant")
                    return None
                case OK(access_token):
                    response.set_content_type("application/json")
                    response.set_data(
                        OAuthTokenResponse(
                            access_token=access_token, scope=format_scopes(granted_scopes)
                        ).model_dump_json()
                    )
                    return None
                case _:
                    assert False
