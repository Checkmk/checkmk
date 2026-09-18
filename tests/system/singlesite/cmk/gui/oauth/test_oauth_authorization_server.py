#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""System-level tests for the OAuth authorization server well-known page.

Verify that, once the MCP server is enabled, the RFC 8414 metadata document
is served at ``check_mk/oauth_authorization_server.py`` -- the path the
system Apache's ``/.well-known/oauth-authorization-server/oauth-<site>`` route
(see ``omdlib.system_apache``) proxies to -- and that it is absent while the
MCP server is disabled.

Enabling the MCP server is handled by the ``mcp_enabled_site`` fixture in
``conftest.py``.
"""

import logging

import pytest
import requests

from tests.testlib.site import Site

_OAUTH_METADATA_ENDPOINT_PATH = "oauth_authorization_server.py"
_MCP_SERVER_CONFIG = "MCP_SERVER"

logger = logging.getLogger(__name__)


@pytest.mark.skip_if_edition("community")
def test_oauth_authorization_server_metadata_absent_when_mcp_disabled(site: Site) -> None:
    """The well-known metadata page 404s while the MCP server is disabled."""
    with site.omd_config(_MCP_SERVER_CONFIG, "off"):
        url = site.internal_url + _OAUTH_METADATA_ENDPOINT_PATH
        response = requests.get(url, timeout=30)
        logger.info("GET %s -> %d", url, response.status_code)
        assert response.status_code == 404


@pytest.mark.skip_if_edition("community")
def test_oauth_authorization_server_metadata_is_served_when_mcp_enabled(
    mcp_enabled_site: Site,
) -> None:
    """The well-known metadata page is served once the MCP server is enabled."""
    url = mcp_enabled_site.internal_url + _OAUTH_METADATA_ENDPOINT_PATH
    response = requests.get(url, timeout=30)
    logger.info("GET %s -> %d", url, response.status_code)

    assert response.status_code == 200
    issuer = response.json()["issuer"]
    assert issuer.endswith(f"/oauth-{mcp_enabled_site.id}"), issuer


@pytest.mark.skip_if_not_edition("cloud", "ultimate", "ultimatemt")
def test_oauth_authorization_server_metadata_supports_cors(mcp_enabled_site: Site) -> None:
    """The metadata endpoint is fetchable cross-origin by browser-based clients.

    Both halves of CORS come from the site Apache (mcp.conf): the GET
    response must carry Access-Control-Allow-Origin for the browser to expose
    it, and a preflight -- triggered by e.g. MCP Inspector's
    MCP-Protocol-Version request header -- must succeed rather than hit the
    Apache-wide OPTIONS block.
    """
    url = mcp_enabled_site.internal_url + _OAUTH_METADATA_ENDPOINT_PATH

    get_response = requests.get(url, headers={"Origin": "http://client.example.com"}, timeout=30)
    logger.info("GET %s -> %d", url, get_response.status_code)
    assert get_response.status_code == 200
    assert get_response.headers["access-control-allow-origin"] == "*"

    preflight = requests.options(
        url,
        headers={
            "Origin": "http://client.example.com",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "mcp-protocol-version",
        },
        timeout=30,
    )
    logger.info("OPTIONS %s -> %d", url, preflight.status_code)
    assert preflight.status_code == 200
    assert preflight.headers["access-control-allow-origin"] == "*"
    assert "mcp-protocol-version" in preflight.headers["access-control-allow-headers"].lower()
