#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re

from omdlib.config_api import Hook, null_action, PortHook

AGENT_RECEIVER = Hook(
    name="AGENT_RECEIVER",
    choices=[("on", "enable"), ("off", "disable")],
    default=lambda _edition: "on",
    activation=null_action,
)

AGENT_RECEIVER_PORT = PortHook(
    name="AGENT_RECEIVER_PORT",
    display_name="agent-receiver port",
    default_port=8000,
    activation=null_action,
    choices=re.compile(r"[0-9]{1,5}$"),
    depends=lambda c: c.get("AGENT_RECEIVER") == "on",
)
