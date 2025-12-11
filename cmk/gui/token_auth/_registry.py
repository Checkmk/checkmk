#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime
from collections.abc import Callable
from dataclasses import dataclass
from typing import override

import cmk.ccc.plugin_registry
from cmk.gui.exceptions import MKMethodNotAllowed, MKNotFound, MKUnauthenticatedException
from cmk.gui.http import Request, Response, response
from cmk.gui.pages import PageContext, PageResult
from cmk.gui.token_auth._exceptions import MKTokenExpiredOrRevokedException
from cmk.gui.token_auth._store import (
    AuthToken,
    get_token_store,
    InvalidToken,
    TokenExpired,
    TokenRevoked,
)
from cmk.gui.utils.security_log_events import AuthenticationFailureEvent
from cmk.utils.log.security_event import log_security_event


class TokenAuthenticatedPage:
    def get(self, token: AuthToken, ctx: PageContext) -> PageResult:
        """Override this to implement the page functionality"""
        raise MKMethodNotAllowed("Method not supported")

    def post(self, token: AuthToken, ctx: PageContext) -> PageResult:
        """Override this to implement the page functionality"""
        raise MKMethodNotAllowed("Method not supported")


@dataclass(frozen=True)
class TokenAuthenticatedEndpoint:
    ident: str
    page: TokenAuthenticatedPage


class TokenAuthenticatedPageRegistry(cmk.ccc.plugin_registry.Registry[TokenAuthenticatedEndpoint]):
    @override
    def plugin_name(self, instance: TokenAuthenticatedEndpoint) -> str:
        return instance.ident


token_authenticated_page_registry = TokenAuthenticatedPageRegistry()


def parse_token_and_validate(
    user_provided_token: str, remote_addr: str | None, now: datetime.datetime
) -> AuthToken:
    token_store = get_token_store()
    try:
        return token_store.verify(user_provided_token, now)
    except InvalidToken as e:
        log_security_event(
            AuthenticationFailureEvent(
                user_error=str(e),
                auth_method="token",
                username=None,
                remote_ip=remote_addr,
            )
        )
        raise MKUnauthenticatedException("Token invalid") from e

    except (TokenExpired, TokenRevoked) as e:
        log_security_event(
            AuthenticationFailureEvent(
                user_error=str(e),
                auth_method="token",
                username=None,
                remote_ip=remote_addr,
            )
        )
        raise MKTokenExpiredOrRevokedException(
            "Token expired or revoked", token_type=e.token_type
        ) from e


def handle_token_page(ident: str, request: Request) -> Callable[[PageContext], Response]:
    token = parse_token_and_validate(
        request.var("cmk-token", ""),
        request.remote_addr,
        datetime.datetime.now(datetime.UTC),
    )
    if (endpoint := token_authenticated_page_registry.get(ident)) is None:
        raise MKNotFound(f"Could not find token authenticated page {ident}")
    # I refrain from logging successful authentications here because every Ajax call would result in
    # a successful authentication, we did the same for basic auth on the rest API
    match request.method:
        case "GET":
            method_func = endpoint.page.get
        case "POST":
            method_func = endpoint.page.post
        case _:
            raise MKMethodNotAllowed("Method not allowed")

    def _call(ctx: PageContext) -> Response:
        method_func(token, ctx)
        return response

    return _call
