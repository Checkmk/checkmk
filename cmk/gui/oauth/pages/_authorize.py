#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import http.client as http_client
import secrets
import urllib.parse
from collections.abc import Callable
from typing import override

from cmk.gui.breadcrumb import Breadcrumb
from cmk.gui.htmllib.header import make_header
from cmk.gui.htmllib.html import html
from cmk.gui.http import request, response
from cmk.gui.i18n import _
from cmk.gui.log import logger
from cmk.gui.logged_in import user
from cmk.gui.oauth.store._auth_code_store import AuthCodeRecord, AuthCodeStore
from cmk.gui.oauth.store.client_store import get_client_store
from cmk.gui.pages import Page, PageContext, PageResult
from cmk.gui.scopes import (
    DEFAULT_SCOPE,
    format_scopes,
    InvalidScopeError,
    parse_scopes,
    ScopeId,
)
from cmk.gui.utils.csrf_token import check_csrf_token
from cmk.gui.utils.security_log_events import OAuthAuthorizationFailureEvent
from cmk.gui.utils.transaction_manager import transactions
from cmk.utils.log.security_event import log_security_event

_SCOPE_REQUESTED_VARNAME = "scope"
_SCOPE_SELECTED_VARNAME = "_scope"

ScopeLabels = {
    ScopeId.READ: _("Read only"),
    ScopeId.WRITE: _("Read & write"),
}


class OAuthAuthorizePage(Page):
    """RFC 6749 section 3.1 authorization endpoint, advertised by the RFC 8414 metadata.

    Requires an active Checkmk login session, enforced by the page registry via
    the missing "noauth:" prefix (see cmk.gui.oauth.registration.register()).
    This is where the token's scope is decided: the consent form offers every
    supported scope, and only the selection is bound to the code, so the
    client's raw scope string never reaches the token.
    """

    def __init__(self, enabled: Callable[[], bool]) -> None:
        self._enabled = enabled

    @override
    def page(self, ctx: PageContext) -> PageResult:
        if not self._enabled():
            response.status_code = http_client.NOT_FOUND
            return None

        redirect_uri = request.var("redirect_uri")
        if redirect_uri is None or urllib.parse.urlsplit(redirect_uri).scheme not in (
            "http",
            "https",
        ):
            # Rejects javascript:/data: etc. here, once, rather than at each
            # place redirect_uri ends up in a href/content attribute below --
            # HTML-escaping alone doesn't neutralize a dangerous URL scheme.
            response.status_code = http_client.BAD_REQUEST
            return None

        client_id = request.var("client_id")
        if client_id is None:
            # Same MUST-NOT-redirect treatment as redirect_uri (RFC 6749
            # section 4.1.2.1): an unknown client's redirect_uri isn't trustworthy.
            response.status_code = http_client.BAD_REQUEST
            return None

        with get_client_store() as store:
            registration = store.get(client_id)

        if registration is None:
            self._log_authorization_failure("unknown client_id")
            response.status_code = http_client.BAD_REQUEST
            return None

        if redirect_uri not in registration.redirect_uris:
            self._log_authorization_failure("redirect_uri not registered for client_id")
            response.status_code = http_client.BAD_REQUEST
            return None

        response_type = request.var("response_type")
        if response_type is None:
            self._error_redirect(ctx, redirect_uri, "invalid_request")
            return None
        if response_type != "code":
            self._error_redirect(ctx, redirect_uri, "unsupported_response_type")
            return None

        code_challenge = request.var("code_challenge")
        if code_challenge is None:
            self._error_redirect(ctx, redirect_uri, "invalid_request")
            return None

        if request.var("code_challenge_method") != "S256":
            self._error_redirect(ctx, redirect_uri, "invalid_request")
            return None

        if len(scope_values := request.values.getlist(_SCOPE_REQUESTED_VARNAME)) > 1:
            # RFC 6749 section 3.1 forbids repeating a request parameter, and
            # with duplicates there is no answer to what the user is approving.
            self._error_redirect(ctx, redirect_uri, "invalid_request")
            return None

        raw_scope = scope_values[0].strip() if scope_values else ""
        try:
            # RFC 6749 section 3.3 leaves what an omitted scope means to us.
            requested_scopes = parse_scopes(raw_scope) if raw_scope else DEFAULT_SCOPE
        except InvalidScopeError as exc:
            # RFC 6749 section 4.1.2.1. Rejected rather than downscoped.
            self._log_authorization_failure(f"unknown scope: {exc}")
            self._error_redirect(ctx, redirect_uri, "invalid_scope")
            return None

        # received authorization form OK
        match request.request_method:
            case "POST":
                self._post(
                    ctx,
                    redirect_uri=redirect_uri,
                    client_id=client_id,
                    code_challenge=code_challenge,
                )
            case "GET" | "HEAD":
                # Werkzeug adds HEAD to every GET route and strips the body.
                self._get(ctx, redirect_uri=redirect_uri, requested_scopes=requested_scopes)
            case _:
                # RFC 6749 section 3.1 gives this endpoint GET and POST, so
                # there is nothing else to answer.
                response.status_code = http_client.METHOD_NOT_ALLOWED
        return None

    def _get(
        self, ctx: PageContext, redirect_uri: str, requested_scopes: frozenset[ScopeId]
    ) -> None:
        client_id = request.var("client_id")

        self._open_center_frame(ctx, _("Authorize access"))
        html.h1(_("Authorize access"))
        if client_id is None:
            html.p(_("An application is requesting access to this Checkmk site."))
        else:
            html.p(
                _('The application "%(client_id)s" is requesting access to this Checkmk site.')
                % {"client_id": client_id}
            )
        # Explicit action: this page is also reachable via the external OAuth
        # issuer alias (/oauth-<site>/authorize, see system_apache.py), where
        # the default relative "oauth_authorize.py" action would resolve
        # against the wrong base path and never reach the backend.
        with html.form_context("oauth_authorize", method="POST", action=request.path):
            html.p(_("It is requesting these permissions:"))
            self._render_scope_choice(requested_scopes)
            html.p(_("Your own user permissions still apply."))
            html.p(_("Redirect target: %(redirect_uri)s") % {"redirect_uri": redirect_uri})
            html.button("_authorize", _("Authorize"), cssclass="hot")
            html.button("_deny", _("Deny"))
            html.hidden_fields()
        self._close_center_frame()

    def _post(
        self,
        ctx: PageContext,
        *,
        redirect_uri: str,
        client_id: str,
        code_challenge: str,
    ) -> None:
        check_csrf_token()
        if not transactions.check_transaction():
            # In the seconds it takes to click Authorize, this transaction id
            # can only already be used -- a double submit or a replay, not
            # staleness -- so it is answered like any other tampered POST.
            self._log_authorization_failure("reused or invalid transaction id")
            self._error_redirect(ctx, redirect_uri, "invalid_request")
            return
        if request.var("_deny") is not None:
            self._error_redirect(ctx, redirect_uri, "access_denied")
            return
        selection = request.var(_SCOPE_SELECTED_VARNAME, "")
        if selection not in (scope.value for scope in ScopeLabels):
            # The rendered form only ever submits an offered scope, so this is
            # a tampered POST, not a user error.
            self._log_authorization_failure("selected scope was not offered")
            self._error_redirect(ctx, redirect_uri, "invalid_request")
            return
        self._issue_code(ctx, redirect_uri, client_id, code_challenge, parse_scopes(selection))

    def _open_center_frame(self, ctx: PageContext, title: str) -> None:
        # Reuses the login/two-factor page chrome: this page is shown before
        # the user reaches the normal, navigable GUI, just like those.
        html.render_headfoot = False
        html.add_body_css_class("login")
        html.add_body_css_class("two_factor")
        make_header(html, title, Breadcrumb())
        # 2.5.0's GUI still wraps content pages in the classic iframe frameset.
        # A standalone page like this one must break out of it, or it renders
        # inside the frame: the sidebar chrome shows around it, and its
        # meta-refresh redirect would navigate the inner frame instead of the
        # whole window. Mirrors the same guard in cmk.gui.login's login page.
        html.javascript(
            """if(top != self) {
    window.top.location.href = location;
}"""
        )
        html.open_div(id_="login")
        html.open_div(id_="login_window")

    def _close_center_frame(self) -> None:
        html.close_div()
        html.close_div()
        html.footer()

    def _issue_code(
        self,
        ctx: PageContext,
        redirect_uri: str,
        client_id: str,
        code_challenge: str,
        selected_scopes: frozenset[ScopeId],
    ) -> None:
        # The bound user is the server-side session user; the page registry
        # guarantees an authenticated session before this code runs.
        assert user.id is not None
        code = secrets.token_urlsafe(32)
        record = AuthCodeRecord(
            user_id=user.id,
            client_id=client_id,
            redirect_uri=redirect_uri,
            # What the consent page showed and the user picked, not the
            # client's raw scope string.
            scope=format_scopes(selected_scopes),
            resource=request.var("resource"),
            code_challenge=code_challenge,
        )
        try:
            AuthCodeStore().store(code, record)
        except Exception:
            # A code without a stored record can never be redeemed; handing it
            # to the client would only feign success. RFC 6749 section 4.1.2.1
            # calls this condition server_error.
            # Deliberately also catches the GUI request timeout (MKTimeout):
            # the client should get the OAuth error redirect.
            logger.exception("failed to persist OAuth authorization code")
            self._error_redirect(ctx, redirect_uri, "server_error")
            return
        params = {"code": code}
        if (state := request.var("state")) is not None:
            params["state"] = state
        self._show_redirect_page(ctx, redirect_uri, params)

    def _log_authorization_failure(self, reason: str) -> None:
        log_security_event(
            OAuthAuthorizationFailureEvent(
                reason=reason,
                client_id=request.var("client_id"),
                remote_ip=request.remote_ip,
            )
        )

    def _error_redirect(self, ctx: PageContext, redirect_uri: str, error: str) -> None:
        params = {"error": error}
        if (state := request.var("state")) is not None:
            params["state"] = state
        self._show_redirect_page(ctx, redirect_uri, params)

    def _show_redirect_page(
        self, ctx: PageContext, redirect_uri: str, params: dict[str, str]
    ) -> None:
        parts = urllib.parse.urlsplit(redirect_uri)
        qs_map = dict(urllib.parse.parse_qsl(parts.query, keep_blank_values=True))
        qs_map.update(params)
        query = urllib.parse.urlencode(list(qs_map.items()))
        target_url = urllib.parse.urlunsplit(parts._replace(query=query))

        self._open_center_frame(ctx, _("Redirecting..."))
        # Not an HTTP redirect: redirect_uri is necessarily cross-origin (the
        # OAuth client's own callback), and Chrome -- unlike Firefox --
        # enforces the site's form-action CSP against redirects resulting
        # from a form submission. A 200 page that navigates via meta-refresh
        # isn't part of that chain, so no CSP directive here restricts it.
        # (A body-placed refresh meta tag is valid HTML5, unlike most other
        # meta variants -- make_header() has already closed <head> for us.)
        html.meta(httpequiv="refresh", content=f"0; url={target_url}")
        html.p(_("Redirecting..."))
        html.a(_("Click here if you are not redirected automatically."), href=target_url)
        self._close_center_frame()

    def _render_scope_choice(self, requested_scopes: frozenset[ScopeId]) -> None:
        # Preselected, so approving an untouched form binds what was asked for.
        as_requested = ScopeId.WRITE if ScopeId.WRITE in requested_scopes else ScopeId.READ
        html.open_p()
        for index, scope in enumerate(ScopeLabels.keys()):
            if index:
                html.br()
            html.radiobutton(
                _SCOPE_SELECTED_VARNAME,
                scope.value,
                checked=scope is as_requested,
                label=ScopeLabels[scope],
            )
        html.close_p()
