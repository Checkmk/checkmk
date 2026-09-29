#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import http.client
from collections.abc import Callable
from datetime import datetime, timedelta, UTC
from http import HTTPStatus
from typing import Final

from cmk.ccc.user import UserId
from cmk.gui.oauth.store.client_store import ClientId, get_client_store
from cmk.gui.oauth.token.token_store import get_token_store
from cmk.gui.openapi.framework import (
    ApiContext,
    APIVersion,
    EndpointBehavior,
    EndpointDoc,
    EndpointHandler,
    EndpointMetadata,
    EndpointPermissions,
    VersionedEndpoint,
)
from cmk.gui.openapi.framework.model.response import ApiResponse
from cmk.gui.openapi.restful_objects.constructors import domain_type_action_href
from cmk.gui.openapi.utils import EXT, ProblemException
from cmk.gui.scopes import (
    format_scopes,
    InvalidScopeError,
    parse_scopes,
    ScopeId,
    SUPPORTED_SCOPES,
)
from cmk.gui.utils.security_log_events import OAuthTokenFailureEvent, OAuthTokenIssuedEvent
from cmk.utils.security_event import log_security_event

from .endpoint_family import GUI_SESSION_FAMILY
from .models.request_models import DelegateSessionRequest
from .models.response_models import DelegateSessionResponse
from .utils import live_session_user, require_site_internal_caller

# Every token this endpoint issues goes to this one client. The fixed id
# sets them apart from the tokens of MCP clients people register.
_AI_CONTROL_PLANE_CLIENT_ID: Final = ClientId("checkmk-ai-control-plane")
_AI_CONTROL_PLANE_CLIENT_NAME: Final = "Checkmk AI Control Plane"

# One token serves one turn of the AI control plane, so it has to outlive
# the longest turn.
_TOKEN_LIFETIME: Final = timedelta(hours=1)


def _requested_scopes(raw: str) -> frozenset[ScopeId]:
    try:
        return parse_scopes(raw)
    except InvalidScopeError:
        # No remote address: the caller is always a site service on the loopback.
        log_security_event(
            OAuthTokenFailureEvent(
                reason="invalid scope", client_id=_AI_CONTROL_PLANE_CLIENT_ID, remote_ip=None
            )
        )
        raise ProblemException(
            status=http.client.BAD_REQUEST,
            title="Invalid scope",
            detail=f"The scope must name one or more of: {', '.join(SUPPORTED_SCOPES)}.",
            ext=EXT({"error": "invalid_scope"}),
        ) from None


def _issue_token(user_id: UserId, *, resource: str, scopes: frozenset[ScopeId]) -> str:
    """A new token for the built-in client, which is created if it is missing."""
    with get_client_store() as clients:
        clients.ensure_builtin(_AI_CONTROL_PLANE_CLIENT_ID, _AI_CONTROL_PLANE_CLIENT_NAME)
    with get_token_store() as tokens:
        issued = tokens.issue_token(
            user_id,
            expires_at=datetime.now(UTC) + _TOKEN_LIFETIME,
            resource=resource,
            scope=scopes,
            client_id=_AI_CONTROL_PLANE_CLIENT_ID,
        )
    if not issued.is_ok():
        # Only if an admin deleted the client right after it was ensured.
        raise ProblemException(
            status=http.client.INTERNAL_SERVER_ERROR,
            title="Cannot issue token",
            detail="The built-in AI control plane client is missing.",
        )
    return issued.ok


def make_delegate_session_endpoint(delegation_enabled: Callable[[], bool]) -> VersionedEndpoint:
    """The delegate endpoint, which answers 404 while delegation_enabled() is false."""

    def delegate_session_v1(
        api_context: ApiContext, body: DelegateSessionRequest
    ) -> ApiResponse[DelegateSessionResponse]:
        """Get an access token for the user behind a GUI session

        The cookie comes in the body, not as a cookie, for the same reason as in
        the identify endpoint. A request that carries the cookie is logged in as
        the cookie's user, and the site-internal secret is then ignored. Any
        script on a Checkmk page could then get a token for its user, because the
        browser adds the cookie by itself.

        The endpoint answers 404 while the AI control plane is switched off.
        """
        require_site_internal_caller(api_context)
        if not delegation_enabled():
            raise ProblemException(
                status=http.client.NOT_FOUND,
                title=http.client.responses[http.client.NOT_FOUND],
                detail="The AI control plane is not enabled on this site.",
            )
        scopes = _requested_scopes(body.scope)
        user_id = live_session_user(api_context, body.session_cookie, endpoint="delegate")
        access_token = _issue_token(user_id, resource=body.resource, scopes=scopes)
        log_security_event(
            OAuthTokenIssuedEvent(user_id=user_id, client_id=_AI_CONTROL_PLANE_CLIENT_ID)
        )
        return ApiResponse(
            DelegateSessionResponse(
                access_token=access_token,
                issued_token_type="urn:ietf:params:oauth:token-type:access_token",
                token_type="Bearer",
                expires_in=int(_TOKEN_LIFETIME.total_seconds()),
                scope=format_scopes(scopes),
                user_id=user_id,
            ),
            status_code=http.client.OK,
            # RFC 6749 section 5.1: a response that carries a token must not be cached.
            headers={"Cache-Control": "no-store"},
        )

    return VersionedEndpoint(
        metadata=EndpointMetadata(
            path=domain_type_action_href("gui_session", "delegate"),
            link_relation="cmk/delegate_session",
            method="post",
        ),
        permissions=EndpointPermissions(required=None),
        doc=EndpointDoc(family=GUI_SESSION_FAMILY.name),
        behavior=EndpointBehavior(skip_locking=True, update_config_generation=False),
        versions={
            APIVersion.INTERNAL: EndpointHandler(
                handler=delegate_session_v1, additional_status_codes=[HTTPStatus.NOT_FOUND]
            )
        },
    )
