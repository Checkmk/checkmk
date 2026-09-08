#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from omdlib.config_api import Hook, null_action

AI_AGENT_ENGINE = Hook(
    name="AI_AGENT_ENGINE",
    default=lambda _edition: "off",
    activation=null_action,
    choices=[("on", "enable"), ("off", "disable")],
)
