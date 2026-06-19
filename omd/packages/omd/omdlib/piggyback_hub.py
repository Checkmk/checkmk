#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from omdlib.config_api import Hook, null_action

PIGGYBACK_HUB = Hook(
    name="PIGGYBACK_HUB",
    choices=[("on", "enable"), ("off", "disable")],
    default=lambda _edition: "off",
    activation=null_action,
)
