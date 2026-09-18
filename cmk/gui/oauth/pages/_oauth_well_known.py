#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import http.client as http_client
from collections.abc import Callable
from typing import override

from cmk.ccc.site import omd_site
from cmk.gui.http import request, response
from cmk.gui.oauth.pages._models import OAuthAuthorizationServerMetadata
from cmk.gui.pages import Page, PageContext, PageResult


class OAuthAuthorizationServerMetadataPage(Page):
    """RFC 8414 authorization server metadata for this site.

    Accessed unauthenticated, proxied here from the system apache's
    /.well-known/oauth-authorization-server/oauth-<site> route. The issuer is
    kept to a single path segment (oauth-<site>, not <site>/check_mk/...): MCP
    clients (observed with Claude Code) don't reliably do RFC 8414's path
    insertion for multi-segment issuer paths, so a single segment is the only
    shape that gets discovered in practice.

    Returns 404 while no OAuth-consuming feature is enabled for the site (the
    enabled predicate is injected at registration). The document is
    intentionally incomplete for now: jwks_uri doesn't exist yet.

    The introspection_endpoint (RFC 7662) is left out as it violates the RFC.
    We assume introspection is only called via the loopback device.
    """

    def __init__(self, enabled: Callable[[], bool]) -> None:
        self._enabled = enabled

    @override
    def page(self, ctx: PageContext) -> PageResult:
        if not self._enabled():
            response.status_code = http_client.NOT_FOUND
            return None

        issuer = f"{request.host_url}oauth-{omd_site()}"
        response.set_content_type("application/json")
        response.set_data(
            OAuthAuthorizationServerMetadata(
                issuer=issuer,
                authorization_endpoint=f"{issuer}/authorize",
                registration_endpoint=f"{issuer}/register",
                token_endpoint=f"{issuer}/token",
            ).model_dump_json()
        )
        return None
