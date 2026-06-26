#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

from omdlib.config_api import Config, Hook


def _write_mcp_apache_conf(site_name: str, site_home: Path, config: Config) -> None:
    conf_path = site_home / "etc" / "apache" / "conf.d" / "mcp.conf"
    if config["MCP_SERVER"] == "on":
        sock = site_home / "tmp" / "run" / "mcp.sock"
        conf_path.write_text(
            f"""\
# Written by MCP_SERVER hook
LoadModule proxy_module /omd/sites/{site_name}/lib/apache/modules/mod_proxy.so
LoadModule proxy_http_module /omd/sites/{site_name}/lib/apache/modules/mod_proxy_http.so

ProxyPass "/{site_name}/check_mk/mcp" "unix://{sock}|http://localhost/" retry=0 timeout=120
ProxyPassReverse "/{site_name}/check_mk/mcp" "unix://{sock}|http://localhost/"
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
