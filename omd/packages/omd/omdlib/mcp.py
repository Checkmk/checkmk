#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from omdlib.config_api import network_port_has_error, null_action, PortHook

MCP_SERVER_PORT = PortHook(
    name="MCP_SERVER_PORT",
    display_name="mcp-server port",
    default_port=8017,
    activation=null_action,
    choices=network_port_has_error,
)
