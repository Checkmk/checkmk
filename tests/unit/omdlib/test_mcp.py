#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

import pytest

from omdlib.mcp import MCP_SERVER, MCP_TRACE_FORWARD

from cmk.ccc.version import Edition


def test_mcp_conf_proxies_the_mcp_route_to_the_daemon_socket_when_enabled(
    tmp_path: Path,
) -> None:
    site_home = tmp_path
    (site_home / "etc" / "apache" / "conf.d").mkdir(parents=True)

    MCP_SERVER.activation("unit", site_home, {"MCP_SERVER": "on"})

    conf = (site_home / "etc" / "apache" / "conf.d" / "mcp.conf").read_text()
    sock = site_home / "tmp" / "run" / "mcp.sock"
    prm = "/.well-known/oauth-protected-resource/unit/check_mk/mcp"
    assert f'ProxyPass "/unit/check_mk/mcp" "unix://{sock}|http://localhost:1" ' in conf
    assert 'ProxyPassReverse "/unit/check_mk/mcp" "http://localhost:1"\n' in conf
    assert f'ProxyPass "{prm}" "unix://{sock}|http://localhost:1{prm}"\n' in conf
    assert f'ProxyPassReverse "{prm}" "http://localhost:1{prm}"\n' in conf


def test_mcp_conf_proxies_the_public_prm_route_when_enabled(tmp_path: Path) -> None:
    site_home = tmp_path
    (site_home / "etc" / "apache" / "conf.d").mkdir(parents=True)

    MCP_SERVER.activation("unit", site_home, {"MCP_SERVER": "on"})

    conf = (site_home / "etc" / "apache" / "conf.d" / "mcp.conf").read_text()
    assert "http://localhost:1/.well-known/oauth-protected-resource/unit/check_mk/mcp" in conf
    assert "ProxyPreserveHost On" in conf
    assert "Require all granted" in conf


def test_mcp_conf_exempts_the_options_preflight_when_enabled(tmp_path: Path) -> None:
    site_home = tmp_path
    (site_home / "etc" / "apache" / "conf.d").mkdir(parents=True)

    MCP_SERVER.activation("unit", site_home, {"MCP_SERVER": "on"})

    conf = (site_home / "etc" / "apache" / "conf.d" / "mcp.conf").read_text()
    assert "RewriteCond %{REQUEST_METHOD} =OPTIONS" in conf
    assert "RewriteRule .* - [L]" in conf


def test_mcp_conf_sets_cors_headers_for_the_oauth_endpoints_when_enabled(tmp_path: Path) -> None:
    site_home = tmp_path
    (site_home / "etc" / "apache" / "conf.d").mkdir(parents=True)

    MCP_SERVER.activation("unit", site_home, {"MCP_SERVER": "on"})

    conf = (site_home / "etc" / "apache" / "conf.d" / "mcp.conf").read_text()
    assert 'Header always set Access-Control-Allow-Origin "*"' in conf
    assert "oauth_(authorization_server|token|client_registration)" in conf


def test_mcp_conf_is_removed_when_disabled(tmp_path: Path) -> None:
    site_home = tmp_path
    conf_dir = site_home / "etc" / "apache" / "conf.d"
    conf_dir.mkdir(parents=True)
    (conf_dir / "mcp.conf").write_text("stale")

    MCP_SERVER.activation("unit", site_home, {"MCP_SERVER": "off"})

    assert not (conf_dir / "mcp.conf").exists()


@pytest.mark.parametrize("edition", list(Edition), ids=lambda e: e.name.lower())
def test_mcp_trace_forward_ships_opted_out(edition: Edition) -> None:
    # Privacy guarantee of CMK-36748: sending usage data is an explicit
    # opt-in, so a fresh site of any edition must default to "off".
    assert MCP_TRACE_FORWARD.default(edition) == "off"
