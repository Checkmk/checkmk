#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections import defaultdict
from pathlib import Path

from omdlib.ai_agent_engine import AI_AGENT_ENGINE
from omdlib.mcp import MCP_SERVER

# mod_proxy pools backend connections by the "scheme://host" after the "|" and
# ignores the socket path, so two hooks sharing an origin would share a pool and
# Apache could answer from the wrong daemon. This is the only check for it: a
# system test cannot force pool reuse with a few sequential requests.
#
# The hook list is explicit. config_hooks._HOOKS holds every hook, but most
# activations need other settings and site directories, so they cannot run in a
# bare tmp site. A new unix-socket hook is added here.
_UNIX_SOCKET_PROXY_HOOKS = [MCP_SERVER, AI_AGENT_ENGINE]


def _sockets_by_origin(conf_dir: Path) -> dict[str, set[str]]:
    sockets_by_origin: dict[str, set[str]] = defaultdict(set)
    for conf_path in conf_dir.glob("*.conf"):
        for line in conf_path.read_text().splitlines():
            words = line.split()
            if words[:1] != ["ProxyPass"]:
                continue
            for word in words:
                if "unix://" not in word:
                    continue
                sock, origin = word.strip('"').removeprefix("unix://").split("|")
                scheme, _, host = origin.split("/")[:3]
                sockets_by_origin[f"{scheme}//{host}"].add(sock)
    return sockets_by_origin


def test_unix_socket_proxy_hooks_use_one_socket_per_origin(tmp_path: Path) -> None:
    site_home = tmp_path
    conf_dir = site_home / "etc" / "apache" / "conf.d"
    conf_dir.mkdir(parents=True)
    for hook in _UNIX_SOCKET_PROXY_HOOKS:
        hook.activation("unit", site_home, {hook.name: "on"})

    assert _sockets_by_origin(conf_dir) == {
        "http://localhost:1": {str(site_home / "tmp" / "run" / "mcp.sock")},
        "http://localhost:2": {str(site_home / "tmp" / "run" / "ai-agent-engine.sock")},
    }
