#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

from omdlib.config_api import Config, Error, Hook

from cmk.flags import load_release_flags


def ai_agent_engine_has_error(value: str) -> None | Error:
    if value not in ("on", "off"):
        return Error("Allowed are: on, off")
    if value == "on" and not load_release_flags(Path("etc/check_mk")).exp_ai_assistant:
        return Error("This experimental testing feature is not enabled.")
    return None


# The route below /{site}/check_mk/ that the site Apache forwards to the daemon.
_ROUTE = "ai-agent-engine"

# Pinned by skel/etc/init.d/ai-agent-engine of the cmk-agent-engine package, which
# pre-creates the socket and passes it to uvicorn as --uds. Keep both in sync.
_SOCKET_REL_PATH = Path("tmp/run/ai-agent-engine.sock")

# mod_proxy pools and reuses backend connections keyed by the "scheme://host[:port]"
# string after the "|". The unix socket path before the "|" plays no part in that
# key, so two unix-socket ProxyPass lines with the same origin string would let
# Apache serve a request meant for one socket over a pooled connection attached to
# the other. mcp.conf uses "http://localhost:1"; this hook uses ":2". Neither port
# is ever dialed: mod_proxy_uds connects to the socket before any TCP connect.
_ORIGIN = "http://localhost:2"


def _write_ai_agent_engine_apache_conf(site_name: str, site_home: Path, config: Config) -> None:
    conf_path = site_home / "etc" / "apache" / "conf.d" / "ai-agent-engine.conf"
    if config["AI_AGENT_ENGINE"] != "on":
        conf_path.unlink(missing_ok=True)
        return

    sock = site_home / _SOCKET_REL_PATH
    route = f"/{site_name}/check_mk/{_ROUTE}"
    conf_path.write_text(
        f"""\
# Written by AI_AGENT_ENGINE hook
# Guard the LoadModule directives against warnings when other hooks load the same modules.
<IfModule !proxy_module>
LoadModule proxy_module /omd/sites/{site_name}/lib/apache/modules/mod_proxy.so
</IfModule>
<IfModule !proxy_http_module>
LoadModule proxy_http_module /omd/sites/{site_name}/lib/apache/modules/mod_proxy_http.so
</IfModule>

# ":2" is not a real port: mod_proxy_uds connects to the unix socket before the
# "|" and never dials it. It only gives this worker an origin string distinct from
# mcp.conf's "http://localhost:1", because mod_proxy pools connections by origin
# and ignores the socket path.
#
# No trailing slash on the target: mod_proxy appends the rest of the request path
# to it, so "{_ORIGIN}/" would forward ".../healthz" as "//healthz", which the
# daemon does not route.
#
# Plain ProxyPass rather than a <Location> block, like mcp.conf. Per-route
# settings for streaming responses come with the endpoint that needs them.
#
# ProxyPassReverse gets the bare origin: it rewrites Location headers by prefix
# match against its argument as written, and the daemon writes "{_ORIGIN}/...",
# never the "unix://...|" form.
ProxyPass "{route}" "unix://{sock}|{_ORIGIN}" retry=0 timeout=120
ProxyPassReverse "{route}" "{_ORIGIN}"
"""
    )


AI_AGENT_ENGINE = Hook(
    name="AI_AGENT_ENGINE",
    default=lambda _edition: "off",
    activation=_write_ai_agent_engine_apache_conf,
    choices=ai_agent_engine_has_error,
)
