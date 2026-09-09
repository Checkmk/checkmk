#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

from omdlib.config_api import Config, Hook, null_action


def _write_mcp_apache_conf(site_name: str, site_home: Path, config: Config) -> None:
    conf_path = site_home / "etc" / "apache" / "conf.d" / "mcp.conf"
    if config["MCP_SERVER"] == "on":
        sock = site_home / "tmp" / "run" / "mcp.sock"
        prm = f"/.well-known/oauth-protected-resource/{site_name}/check_mk/mcp"
        conf_path.write_text(
            f"""\
# Written by MCP_SERVER hook
# Guard the LoadModule directives: other hooks (e.g. TRACE_RECEIVE/jaeger) may
# already have loaded these proxy modules. Without the guards Apache logs
# "AH01574: module ... is already loaded, skipping" on startup.
<IfModule !proxy_module>
LoadModule proxy_module /omd/sites/{site_name}/lib/apache/modules/mod_proxy.so
</IfModule>
<IfModule !proxy_http_module>
LoadModule proxy_http_module /omd/sites/{site_name}/lib/apache/modules/mod_proxy_http.so
</IfModule>

ProxyPass "/{site_name}/check_mk/mcp" "unix://{sock}|http://localhost:1/" retry=0 timeout=120
ProxyPassReverse "/{site_name}/check_mk/mcp" "unix://{sock}|http://localhost:1/"

# No retry=/timeout= here: mod_proxy keys workers by the socket origin (the
# "unix://...sock|http://localhost:1" prefix, path excluded), so this ProxyPass
# reuses the worker the "/{site_name}/check_mk/mcp" line above already defined.
# Those parameters are worker-scoped and set there; repeating them is ignored
# ("AH01146: Ignoring parameter ... because of worker sharing" at startup).
ProxyPass "{prm}" "unix://{sock}|http://localhost:1{prm}"
ProxyPassReverse "{prm}" "unix://{sock}|http://localhost:1{prm}"

# OAuth 2.0 Protected Resource Metadata (RFC 9728). Public discovery document,
# proxied to the MCP server preserving the full path so its PRM route matches.
<Location "{prm}">
  ProxyPreserveHost On
  Require all granted
</Location>

# Browser-based MCP clients (MCP Inspector, web IDEs) send CORS preflights, so
# OPTIONS must reach the MCP endpoint, the OAuth discovery/registration/token
# endpoints and the RFC 9728 well-known path. These live here, gated by the
# MCP_SERVER hook, not in the always-shipped security.conf: they only make sense
# when the MCP server runs. mcp.conf sorts before security.conf under
# conf.d/*.conf, so this [L] short-circuits security.conf's OPTIONS->405 rewrite.
# oauth_authorize.py is deliberately NOT exempted (top-level navigation, never
# preflights). The RFC 8414 authorization-server well-known path arrives here as
# /<site>/check_mk/oauth_authorization_server.py (rewritten by the system apache,
# see omdlib.system_apache), so it is matched under that name.
<IfModule mod_rewrite.c>
  RewriteEngine on
  RewriteCond %{{REQUEST_METHOD}} =OPTIONS
  RewriteCond %{{REQUEST_URI}} ^/[^/]+/check_mk/(mcp/?$|oauth_(authorization_server|token|client_registration)\\.py$) [OR]
  RewriteCond %{{REQUEST_URI}} ^/\\.well-known/oauth-protected-resource/
  RewriteRule .* - [L]
</IfModule>

# CORS for the GUI-served OAuth endpoints consumed by browser-based MCP clients:
# the responses need Access-Control-Allow-Origin for the browser to expose them,
# and the preflight (a bare 200 from the GUI routing) needs the Allow-* set. The
# MCP endpoint and the RFC 9728 document are NOT listed: the MCP server sends its
# own CORS headers, and doubling them up would make browsers reject the response.
<IfModule mod_headers.c>
  <LocationMatch "^/[^/]+/check_mk/oauth_(authorization_server|token|client_registration)\\.py$">
    Header always set Access-Control-Allow-Origin "*"
    Header always set Access-Control-Allow-Methods "GET, POST, OPTIONS"
    Header always set Access-Control-Allow-Headers "Authorization, Content-Type, Mcp-Protocol-Version"
  </LocationMatch>
</IfModule>
"""
        )
    else:
        conf_path.unlink(missing_ok=True)


MCP_SERVER = Hook(
    name="MCP_SERVER",
    default=lambda _edition: "off",
    activation=_write_mcp_apache_conf,
    choices=[("on", "enable"), ("off", "disable")],
)

# Opt-in gate for forwarding the MCP server's traces (usage data) to Checkmk's
# central telemetry collector, independent of the site-wide TRACE_SEND
# pipeline: spans go to both. The collector endpoint and its ingest-only
# bearer token are built into the non-free MCP server code (cmk.mcp._tracing).
MCP_TRACE_FORWARD = Hook(
    name="MCP_TRACE_FORWARD",
    default=lambda _edition: "off",
    activation=null_action,
    choices=[("on", "enable"), ("off", "disable")],
)
